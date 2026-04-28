from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.passenger import Passenger
from app.models.driver import Driver
from app.models.admin import Admin
from app.services.auth_service import verify_password, hash_password, create_access_token
from app.schemas.auth import (
    PassengerRegisterRequest,
    PassengerLoginRequest,
    DriverLoginRequest,
    AdminLoginRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/passenger/register", response_model=TokenResponse)
async def passenger_register(data: PassengerRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.passenger,
        phone_number=data.phone_number,
    )
    db.add(user)
    await db.flush()

    passenger = Passenger(
        passenger_id=user.id,
        university_id=data.university_id,
        student_type=data.student_type,
    )
    db.add(passenger)
    await db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return {"access_token": token}


@router.post("/passenger/login")
async def passenger_login(data: PassengerLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email, User.role == UserRole.passenger)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(str(user.id), user.role.value)
    return {"access_token": token, "token_type": "bearer", "user": UserOut.model_validate(user)}


@router.post("/driver/login")
async def driver_login(data: DriverLoginRequest, db: AsyncSession = Depends(get_db)):
    driver_result = await db.execute(select(Driver).where(Driver.driver_code == data.driver_code))
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=401, detail="Invalid driver code")

    user_result = await db.execute(select(User).where(User.id == driver.driver_id))
    user = user_result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    bus_number = None
    route_number = None
    if driver.assigned_bus:
        bus_number = driver.assigned_bus.bus_number
        if driver.assigned_bus.route:
            route_number = driver.assigned_bus.route.route_number

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver_code": driver.driver_code,
        "full_name": user.full_name,
        "bus_number": bus_number,
        "route_number": route_number,
    }


@router.post("/admin/login")
async def admin_login(data: AdminLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        select(User).where(User.email == data.email, User.role == UserRole.admin)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin_result = await db.execute(select(Admin).where(Admin.admin_id == user.id))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin profile not found")

    now = datetime.now(timezone.utc)

    # Check account lock
    if admin.locked_until:
        locked_until_aware = admin.locked_until
        if locked_until_aware.tzinfo is None:
            locked_until_aware = locked_until_aware.replace(tzinfo=timezone.utc)
        if locked_until_aware > now:
            remaining = int((locked_until_aware - now).total_seconds())
            raise HTTPException(
                status_code=423,
                detail=f"Account locked. Try again in {remaining} seconds",
            )

    if not verify_password(data.password, user.password_hash):
        admin.failed_login_count = (admin.failed_login_count or 0) + 1
        if admin.failed_login_count >= 3:
            admin.locked_until = now + timedelta(minutes=15)
            await db.commit()
            raise HTTPException(
                status_code=423,
                detail="Account locked for 15 minutes due to too many failed attempts",
            )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Successful login
    admin.failed_login_count = 0
    admin.locked_until = None
    admin.last_login_at = now
    await db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin_id": str(admin.admin_id),
        "full_name": user.full_name,
        "email": user.email,
    }


@router.post("/logout", response_model=MessageResponse)
async def logout():
    # JWT is stateless; invalidation is handled client-side
    return {"message": "Logged out successfully"}
