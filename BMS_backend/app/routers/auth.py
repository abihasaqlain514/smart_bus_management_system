from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.passenger import Passenger
from app.models.driver import Driver, DriverStatus
from app.models.admin import Admin
from app.services.auth_service import verify_password, hash_password, create_access_token

from app.schemas.passenger import PassengerRegisterRequest, PassengerLoginRequest
from app.schemas.driver import DriverRegisterRequest, DriverLoginRequest
from app.schemas.admin import AdminRegisterRequest, AdminLoginRequest
from app.schemas.auth import TokenResponse, UserOut, LogoutResponse
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Passenger ─────────────────────────────────────────────────────────────────

@router.post("/passenger/register", status_code=201,
             summary="Register a new passenger")
async def passenger_register(data: PassengerRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered — use /passenger/login instead")

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
        gender=data.gender.value if data.gender else "other",
    )
    db.add(passenger)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token":  token,
        "token_type":    "bearer",
        "user_id":       str(user.id),
        "role":          user.role.value,
        "full_name":     user.full_name,
        "email":         user.email,
        "university_id": data.university_id,
        "student_type":  data.student_type,
    }


@router.post("/passenger/login", summary="Passenger login")
async def passenger_login(data: PassengerLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email, User.role == UserRole.passenger)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
    }


# ── Driver ────────────────────────────────────────────────────────────────────

@router.post("/driver/register", status_code=201, summary="Driver self-registration")
async def driver_register(data: DriverRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Unique email check
    existing_email = await db.execute(select(User).where(User.email == data.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Unique driver_code check
    existing_code = await db.execute(
        select(Driver).where(Driver.driver_code == data.driver_code.strip().upper())
    )
    if existing_code.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Driver code is already in use")

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
        driver_code=data.driver_code.strip().upper(),
        license_number=data.license_number,
        license_expiry_date=data.license_expiry_date,
        experience_years=data.experience_years,
        status=DriverStatus.offline,
    )
    db.add(driver)
    await db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver_id": str(user.id),
        "driver_code": driver.driver_code,
        "full_name": user.full_name,
        "email": user.email,
        "status": driver.status.value,
        "message": "Registration successful. Your account is pending admin approval.",
    }


@router.post("/driver/login", summary="Driver login")
async def driver_login(data: DriverLoginRequest, db: AsyncSession = Depends(get_db)):
    driver_result = await db.execute(
        select(Driver).where(Driver.driver_code == data.driver_code.strip().upper())
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=401, detail="Invalid driver code or password")

    user_result = await db.execute(select(User).where(User.id == driver.driver_id))
    user = user_result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid driver code or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    if driver.status == DriverStatus.suspended:
        raise HTTPException(status_code=403, detail="Driver account is suspended")

    bus_number = route_name = route_number = None
    bus_route_id = None
    if driver.assigned_bus:
        bus_number = driver.assigned_bus.bus_number
        if driver.assigned_bus.route:
            bus_route_id = str(driver.assigned_bus.route.id)
            route_name   = driver.assigned_bus.route.route_name
            route_number = driver.assigned_bus.route.route_number

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver_id": str(driver.driver_id),
        "driver_code": driver.driver_code,
        "full_name": user.full_name,
        "email": user.email,
        "status": driver.status.value,
        "is_online": driver.is_online,
        "assigned_bus_id": str(driver.assigned_bus_id) if driver.assigned_bus_id else None,
        "bus_number": bus_number,
        "bus_route_id": bus_route_id,
        "route_name": route_name,
        "route_number": route_number,
    }


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.post("/admin/register", status_code=201, summary="Admin registration")
async def admin_register(data: AdminRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.admin,
        phone_number=data.phone_number,
    )
    db.add(user)
    await db.flush()

    admin = Admin(
        admin_id=user.id,
        department=data.department,
        permissions={},
    )
    db.add(admin)
    await db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin_id": str(admin.admin_id),
        "full_name": user.full_name,
        "email": user.email,
        "department": admin.department,
        "message": "Admin account created successfully.",
    }


@router.post("/admin/login", summary="Admin login")
async def admin_login(data: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        select(User).where(User.email == data.email, User.role == UserRole.admin)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    admin_result = await db.execute(select(Admin).where(Admin.admin_id == user.id))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin profile not found")

    now = datetime.now(timezone.utc)

    # Lock check
    if admin.locked_until:
        locked_until = admin.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            remaining = int((locked_until - now).total_seconds())
            raise HTTPException(
                status_code=423,
                detail=f"Account locked. Try again in {remaining} seconds.",
            )

    if not verify_password(data.password, user.password_hash):
        admin.failed_login_count = (admin.failed_login_count or 0) + 1
        if admin.failed_login_count >= 3:
            admin.locked_until = now + timedelta(minutes=15)
            await db.commit()
            raise HTTPException(
                status_code=423,
                detail="Account locked for 15 minutes due to too many failed attempts.",
            )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Successful login — reset counters
    admin.failed_login_count = 0
    admin.locked_until = None
    admin.last_login_at = now
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    await db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin_id": str(admin.admin_id),
        "full_name": user.full_name,
        "email": user.email,
        "department": admin.department,
        "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None,
    }


# ── Logout (stateless JWT — client drops the token) ───────────────────────────

@router.post("/logout", response_model=LogoutResponse, summary="Logout")
async def logout():
    return LogoutResponse()
