from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.schemas.admin import BusAssignRequest
from app.services.auth_service import hash_password
from app.services.analytics_service import get_analytics

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_admin_id(admin_user: User) -> UUID:
    """Extract admin_id safely from the user's admin_profile relationship."""
    if admin_user.admin_profile:
        return admin_user.admin_profile.admin_id
    raise HTTPException(status_code=500, detail="Admin profile not loaded")


# ── Users ─────────────────────────────────────────────────────────────────────

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

    old_active = user.is_active
    user.is_active = not user.is_active

    db.add(AuditLog(
        admin_id=_get_admin_id(admin),
        action="BLOCK_USER" if not user.is_active else "UNBLOCK_USER",
        table_name="users",
        record_id=str(user_id),
        old_value={"is_active": old_active},
        new_value={"is_active": user.is_active},
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
        admin_id=_get_admin_id(admin),
        action="DELETE_USER",
        table_name="users",
        record_id=str(user_id),
        old_value={"email": user.email, "role": user.role.value},
    ))
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


# ── Drivers ───────────────────────────────────────────────────────────────────

@router.post("/drivers", response_model=DriverOut, status_code=201)
async def create_driver(
    data: DriverCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")

    existing_code = await db.execute(
        select(Driver).where(Driver.driver_code == data.driver_code.upper())
    )
    if existing_code.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Driver code already in use")

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
        driver_code=data.driver_code.upper(),
        license_number=data.license_number,
        approved_by=_get_admin_id(admin),
    )
    db.add(driver)

    db.add(AuditLog(
        admin_id=_get_admin_id(admin),
        action="CREATE_DRIVER",
        table_name="drivers",
        record_id=str(user.id),
        new_value={"driver_code": data.driver_code, "email": data.email},
    ))
    await db.commit()
    await db.refresh(user)
    await db.refresh(driver)

    # DriverOut expects both User and Driver fields — build manually
    return DriverOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        is_active=user.is_active,
        created_at=user.created_at,
        driver_id=driver.driver_id,
        driver_code=driver.driver_code,
        license_number=driver.license_number,
        is_online=driver.is_online,
        status=driver.status,
        avg_rating=driver.avg_rating,
        total_trips=driver.total_trips,
    )


# ── Selector data (for frontend dropdowns) ───────────────────────────────────

@router.get("/selector-data")
async def selector_data(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Returns buses, drivers, and routes as human-readable lists for dropdown selection."""
    from app.models.route import Route

    buses_res  = await db.execute(select(Bus).where(Bus.is_active == True))
    buses      = buses_res.scalars().all()

    drivers_res = await db.execute(
        select(User, Driver)
        .join(Driver, Driver.driver_id == User.id)
        .where(User.is_active == True)
    )
    driver_rows = drivers_res.all()

    routes_res = await db.execute(select(Route).where(Route.is_active == True))
    routes     = routes_res.scalars().all()

    return {
        "buses": [
            {
                "id": str(b.id),
                "bus_number": b.bus_number,
                "model": b.model or "",
                "status": b.status.value,
                "capacity": b.capacity,
            }
            for b in buses
        ],
        "drivers": [
            {
                "id": str(u.id),
                "driver_code": d.driver_code,
                "full_name": u.full_name,
                "status": d.status.value if d.status else "available",
            }
            for u, d in driver_rows
        ],
        "routes": [
            {
                "id": str(r.id),
                "route_number": r.route_number,
                "route_name": r.route_name,
                "start_point": r.start_point,
                "end_point": r.end_point,
            }
            for r in routes
        ],
    }


# ── Human-readable bus assignment (no UUIDs needed) ───────────────────────────

@router.post("/assign-bus")
async def assign_bus(
    data: BusAssignRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Assign a driver and/or route to a bus using human-readable codes.
    No UUIDs needed — just bus number, driver code, and route number.
    """
    from app.models.route import Route
    from app.models.bus import BusStatus
    from sqlalchemy import update as sql_update

    bus_number   = data.bus_number
    driver_code  = data.driver_code
    route_number = data.route_number
    bus_status   = data.bus_status

    if not bus_number:
        raise HTTPException(status_code=422, detail="bus_number is required")

    bus_res = await db.execute(select(Bus).where(Bus.bus_number == bus_number, Bus.is_active == True))
    bus = bus_res.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus '{bus_number}' not found or inactive")

    updates: dict = {}

    # Resolve driver code → driver user id
    if driver_code:
        drv_res = await db.execute(select(Driver).where(Driver.driver_code == driver_code))
        drv = drv_res.scalar_one_or_none()
        if not drv:
            raise HTTPException(status_code=404, detail=f"Driver code '{driver_code}' not found")
        updates["driver_id"] = drv.driver_id
        # Update driver's assigned_bus_id
        await db.execute(
            sql_update(Driver)
            .where(Driver.driver_id == drv.driver_id)
            .values(assigned_bus_id=bus.id, status=DriverStatus.available)
            .execution_options(synchronize_session=False)
        )

    # Resolve route number → route id
    if route_number:
        rt_res = await db.execute(select(Route).where(Route.route_number == route_number))
        rt = rt_res.scalar_one_or_none()
        if not rt:
            raise HTTPException(status_code=404, detail=f"Route '{route_number}' not found")
        updates["route_id"] = rt.id

    # Bus status
    if bus_status:
        try:
            updates["status"] = BusStatus(bus_status)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status '{bus_status}'")

    if not updates:
        raise HTTPException(status_code=422, detail="Nothing to update — provide at least one of: driver_code, route_number, bus_status")

    await db.execute(
        sql_update(Bus)
        .where(Bus.id == bus.id)
        .values(**updates)
        .execution_options(synchronize_session=False)
    )

    db.add(AuditLog(
        admin_id=_get_admin_id(admin),
        action="ASSIGN_BUS",
        table_name="buses",
        record_id=str(bus.id),
        new_value={k: str(v) for k, v in updates.items()},
    ))
    await db.commit()
    return {"message": f"Bus {bus_number} updated successfully", "updates": {k: str(v) for k, v in updates.items()}}


# ── Monitoring ────────────────────────────────────────────────────────────────

@router.get("/monitoring")
async def monitoring(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.gps_service import get_latest_bus_location

    result = await db.execute(select(Bus).where(Bus.is_active == True))
    buses = result.scalars().all()

    data = []
    for bus in buses:
        loc = await get_latest_bus_location(db, bus.id)
        driver = bus.current_driver          # loaded via selectin relationship
        driver_user = driver.user if driver else None

        data.append({
            "bus_id": str(bus.id),
            "bus_number": bus.bus_number,
            "status": bus.status.value,
            "available_seats": bus.available_seats,
            "capacity": bus.capacity,
            "driver_name": driver_user.full_name if driver_user else None,
            "driver_code": driver.driver_code if driver else None,
            "route_name": bus.route.route_name if bus.route else None,
            "route_number": bus.route.route_number if bus.route else None,
            "latitude": float(loc.latitude) if loc else None,
            "longitude": float(loc.longitude) if loc else None,
            "last_seen": loc.recorded_at.isoformat() if loc else None,
        })
    return data


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def analytics(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return await get_analytics(db)


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()
    total = await db.scalar(select(func.count(AuditLog.id)))
    return {"items": logs, "total": total, "page": page, "page_size": page_size}


# ── Issue Reports ─────────────────────────────────────────────────────────────

@router.post("/issues/{issue_id}/acknowledge")
async def acknowledge_issue(
    issue_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    result = await db.execute(select(IssueReport).where(IssueReport.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue report not found")

    issue.status = IssueStatus.acknowledged
    db.add(AuditLog(
        admin_id=_get_admin_id(admin),
        action="ACKNOWLEDGE_ISSUE",
        table_name="issue_reports",
        record_id=str(issue_id),
    ))
    await db.commit()
    return {"message": "Issue acknowledged", "issue_id": str(issue_id)}
