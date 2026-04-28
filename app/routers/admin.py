from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.database import get_db
from app.deps import require_admin
from app.models.user import User, UserRole
from app.models.driver import Driver, DriverStatus
from app.models.admin import Admin
from app.models.bus import Bus
from app.models.issue_report import IssueReport, IssueStatus
from app.models.audit_log import AuditLog
from app.schemas.auth import UserOut
from app.schemas.driver import DriverCreate, DriverOut
from app.services.auth_service import hash_password
from app.services.analytics_service import get_analytics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserOut])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    role: Optional[UserRole] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    offset = (page - 1) * page_size
    query = select(User)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/block")
async def toggle_block(user_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    old_val = {"is_active": not user.is_active}
    new_val = {"is_active": user.is_active}

    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="BLOCK_USER" if not user.is_active else "UNBLOCK_USER",
        table_name="users",
        record_id=str(user_id),
        old_value=old_val,
        new_value=new_val,
    ))
    await db.commit()
    return {"message": f"User {'blocked' if not user.is_active else 'unblocked'}", "is_active": user.is_active}


@router.delete("/users/{user_id}")
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="DELETE_USER",
        table_name="users",
        record_id=str(user_id),
        old_value={"email": user.email, "role": user.role.value},
    ))
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


@router.post("/drivers", response_model=DriverOut)
async def create_driver(data: DriverCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.driver,
        phone_number=data.phone_number,
    )
    db.add(user)
    await db.flush()

    driver = Driver(
        driver_id=user.id,
        driver_code=data.driver_code,
        license_number=data.license_number,
        approved_by=admin.admin_profile.admin_id,
    )
    db.add(driver)

    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="CREATE_DRIVER",
        table_name="drivers",
        record_id=str(user.id),
        new_value={"driver_code": data.driver_code, "email": data.email},
    ))
    await db.commit()
    await db.refresh(driver)
    return driver


@router.get("/monitoring")
async def monitoring(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.gps_service import get_latest_bus_location
    result = await db.execute(select(Bus).where(Bus.is_active == True))
    buses = result.scalars().all()

    data = []
    for bus in buses:
        loc = await get_latest_bus_location(db, bus.id)
        driver_name = None
        if bus.current_driver:
            driver_result = await db.execute(
                select(User).where(User.id == bus.current_driver.driver_id)
            )
            driver_user = driver_result.scalar_one_or_none()
            driver_name = driver_user.full_name if driver_user else None

        data.append({
            "bus_id": str(bus.id),
            "bus_number": bus.bus_number,
            "status": bus.status.value,
            "available_seats": bus.available_seats,
            "driver_name": driver_name,
            "driver_code": bus.current_driver.driver_code if bus.current_driver else None,
            "route_name": bus.route.route_name if bus.route else None,
            "latitude": float(loc.latitude) if loc else None,
            "longitude": float(loc.longitude) if loc else None,
            "last_seen": loc.recorded_at.isoformat() if loc else None,
        })
    return data


@router.get("/analytics")
async def analytics(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return await get_analytics(db)


@router.get("/logs")
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    total = await db.scalar(select(func.count(AuditLog.id)))
    return {"items": logs, "total": total, "page": page, "page_size": page_size}


@router.post("/issues/{issue_id}/acknowledge")
async def acknowledge_issue(issue_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(IssueReport).where(IssueReport.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue report not found")

    issue.status = IssueStatus.acknowledged
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="ACKNOWLEDGE_ISSUE",
        table_name="issue_reports",
        record_id=str(issue_id),
    ))
    await db.commit()
    return {"message": "Issue acknowledged"}
