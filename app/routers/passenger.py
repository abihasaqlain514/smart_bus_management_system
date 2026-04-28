from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import require_passenger
from app.models.user import User
from app.models.passenger import Passenger
from app.schemas.passenger import PassengerUpdate, PassengerOut

router = APIRouter(prefix="/passenger", tags=["passenger"])


def _build_passenger_out(user: User, passenger: Passenger) -> PassengerOut:
    return PassengerOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        profile_picture=user.profile_picture,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        passenger_id=passenger.passenger_id,
        university_id=passenger.university_id,
        department=passenger.department,
        student_type=passenger.student_type,
        is_hostel_resident=passenger.is_hostel_resident,
        preferred_route_id=passenger.preferred_route_id,
    )


@router.get("/profile", response_model=PassengerOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_passenger),
):
    result = await db.execute(select(Passenger).where(Passenger.passenger_id == user.id))
    passenger = result.scalar_one_or_none()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger profile not found")
    return _build_passenger_out(user, passenger)


@router.patch("/profile", response_model=PassengerOut)
async def update_profile(
    data: PassengerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_passenger),
):
    result = await db.execute(select(Passenger).where(Passenger.passenger_id == user.id))
    passenger = result.scalar_one_or_none()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger profile not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone_number is not None:
        user.phone_number = data.phone_number
    if data.profile_picture is not None:
        user.profile_picture = data.profile_picture
    if data.fcm_token is not None:
        user.fcm_token = data.fcm_token
    if data.department is not None:
        passenger.department = data.department
    if data.is_hostel_resident is not None:
        passenger.is_hostel_resident = data.is_hostel_resident
    if data.preferred_route_id is not None:
        passenger.preferred_route_id = data.preferred_route_id

    await db.commit()
    await db.refresh(user)
    await db.refresh(passenger)
    return _build_passenger_out(user, passenger)
