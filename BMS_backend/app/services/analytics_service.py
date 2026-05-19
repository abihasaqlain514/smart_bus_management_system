from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserRole
from app.models.bus import Bus
from app.models.route import Route
from app.models.booking import Booking, BookingStatus
from app.models.trip import Trip, TripStatus


async def get_analytics(db: AsyncSession) -> dict:
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total_buses = await db.scalar(
        select(func.count(Bus.id)).where(Bus.is_active == True)
    )
    active_routes = await db.scalar(
        select(func.count(Route.id)).where(Route.is_active == True)
    )
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    total_passengers = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.passenger, User.is_active == True
        )
    )
    total_drivers = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.driver, User.is_active == True
        )
    )
    active_trips = await db.scalar(
        select(func.count(Trip.id)).where(Trip.status == TripStatus.active)
    )

    # Peak hour: find the hour with most bookings
    peak_hour = await _get_peak_hour(db)

    return {
        "total_users": total_users or 0,
        "total_passengers": total_passengers or 0,
        "total_drivers": total_drivers or 0,
        "total_buses": total_buses or 0,
        "active_routes": active_routes or 0,
        "total_bookings": total_bookings or 0,
        "active_trips": active_trips or 0,
        "peak_hour": peak_hour,
    }


async def _get_peak_hour(db: AsyncSession) -> Optional[int]:
    from typing import Optional

    result = await db.execute(
        select(
            func.extract("hour", Booking.booked_at).label("hour"),
            func.count(Booking.id).label("cnt"),
        )
        .group_by(func.extract("hour", Booking.booked_at))
        .order_by(func.count(Booking.id).desc())
        .limit(1)
    )
    row = result.one_or_none()
    return int(row.hour) if row else None
