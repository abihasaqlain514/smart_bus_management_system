from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID
from datetime import date

from app.database import get_db
from app.deps import require_passenger, require_driver, require_admin, get_current_user
from app.models.booking import Booking, BookingStatus
from app.models.passenger import Passenger
from app.schemas.booking import BookingCreate, BookingCancel, BookingOut
from app.services.booking_service import create_booking, cancel_booking


async def _enrich_bookings_with_gender(db: AsyncSession, bookings: list) -> list:
    """Attach passenger_gender to each booking dict for seat layout display."""
    results = []
    for b in bookings:
        p = await db.get(Passenger, b.passenger_id)
        obj = BookingOut.model_validate(b)
        obj.passenger_gender = p.gender if p else "other"
        results.append(obj)
    return results

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut)
async def book_seat(data: BookingCreate, db: AsyncSession = Depends(get_db), user=Depends(require_passenger)):
    passenger_result = await db.execute(select(Passenger).where(Passenger.passenger_id == user.id))
    passenger = passenger_result.scalar_one_or_none()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger profile not found")

    return await create_booking(db, user.id, data)


@router.get("/my", response_model=List[BookingOut])
async def my_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_passenger),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Booking)
        .where(Booking.passenger_id == user.id)
        .order_by(Booking.booked_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_my_booking(booking_id: UUID, data: BookingCancel, db: AsyncSession = Depends(get_db), user=Depends(require_passenger)):
    return await cancel_booking(db, booking_id, user.id, data.cancellation_reason)


@router.get("/bus/{bus_id}", response_model=List[BookingOut])
async def get_bus_bookings_today(
    bus_id: UUID,
    booking_date: date = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),   # passengers, drivers, and admins can all view
):
    target_date = booking_date or date.today()
    result = await db.execute(
        select(Booking).where(
            Booking.bus_id == bus_id,
            Booking.booking_date == target_date,
            Booking.status != BookingStatus.cancelled,
        )
    )
    bookings = result.scalars().all()
    return await _enrich_bookings_with_gender(db, bookings)


@router.get("/", response_model=List[BookingOut])
async def all_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Booking)
        .order_by(Booking.booked_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()
