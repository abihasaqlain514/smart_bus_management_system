from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.booking import Booking, BookingStatus
from app.models.bus import Bus
from app.schemas.booking import BookingCreate


async def create_booking(db: AsyncSession, passenger_id: UUID, data: BookingCreate) -> Booking:
    # Verify bus exists and is active
    bus_result = await db.execute(select(Bus).where(Bus.id == data.bus_id, Bus.is_active == True))
    bus = bus_result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found or inactive")

    if bus.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats on this bus")

    # Check uniqueness constraint (bus_id, seat_number, booking_date)
    existing = await db.execute(
        select(Booking).where(
            Booking.bus_id == data.bus_id,
            Booking.seat_number == data.seat_number,
            Booking.booking_date == data.booking_date,
            Booking.status != BookingStatus.cancelled,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Seat already booked for this date")

    # Validate seat number
    if data.seat_number < 1 or data.seat_number > bus.capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid seat number. Must be between 1 and {bus.capacity}",
        )

    booking = Booking(
        passenger_id=passenger_id,
        bus_id=data.bus_id,
        route_id=data.route_id,
        seat_number=data.seat_number,
        booking_date=data.booking_date,
        status=BookingStatus.confirmed,
    )
    db.add(booking)

    # Decrement available seats
    bus.available_seats -= 1

    await db.commit()
    await db.refresh(booking)
    return booking


async def cancel_booking(
    db: AsyncSession,
    booking_id: UUID,
    passenger_id: UUID,
    reason: str = None,
) -> Booking:
    from datetime import datetime, timezone

    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.passenger_id == passenger_id,
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Booking already cancelled")

    booking.status = BookingStatus.cancelled
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancellation_reason = reason

    # Restore seat
    bus_result = await db.execute(select(Bus).where(Bus.id == booking.bus_id))
    bus = bus_result.scalar_one_or_none()
    if bus:
        bus.available_seats += 1

    await db.commit()
    await db.refresh(booking)
    return booking
