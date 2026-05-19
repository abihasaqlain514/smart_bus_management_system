from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps import require_driver, get_current_user
from app.models.trip import Trip, TripStatus
from app.models.bus import Bus, BusStatus
from app.models.driver import Driver, DriverStatus
from app.models.route import Route
from app.schemas.trip import TripStart, TripStatusUpdate, TripSeatUpdate, TripOut, ETAResponse
from app.services.gps_service import calculate_eta
from app.websockets.manager import connection_manager

router = APIRouter(prefix="/trips", tags=["trips"])


async def _fetch_trip_out(db: AsyncSession, trip_id: UUID) -> TripOut:
    """Re-query only the scalar columns needed for TripOut (avoids triggering selectin cascade)."""
    row = (await db.execute(
        select(
            Trip.id, Trip.driver_id, Trip.bus_id, Trip.route_id, Trip.status,
            Trip.started_at, Trip.ended_at, Trip.total_distance_km,
            Trip.total_passengers, Trip.created_at,
        ).where(Trip.id == trip_id)
    )).mappings().one()
    return TripOut(**dict(row))


@router.post("/start", response_model=TripOut)
async def start_trip(data: TripStart, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    # Validate with column-only queries — avoid loading ORM objects with selectin cascade
    if not (await db.execute(select(Driver.driver_id).where(Driver.driver_id == user.id))).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Driver profile not found")

    bus_check = await db.execute(select(Bus.id, Bus.is_active).where(Bus.id == data.bus_id))
    bus_row = bus_check.one_or_none()
    if not bus_row:
        raise HTTPException(status_code=404, detail="Bus not found — ask admin to assign you an active bus")
    if not bus_row.is_active:
        raise HTTPException(status_code=400, detail="Bus is deactivated — ask admin to activate your bus")

    if not (await db.execute(select(Route.id).where(Route.id == data.route_id))).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route not found — ask admin to assign a route to your bus")

    trip = Trip(
        driver_id=user.id,
        bus_id=data.bus_id,
        route_id=data.route_id,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.flush()  # assign trip.id before the UPDATE statements

    # Use raw SQL UPDATE to avoid the circular FK dependency:
    # buses.driver_id → drivers  AND  drivers.assigned_bus_id → buses
    # would cause a CircularDependencyError in SQLAlchemy's ORM flush.
    await db.execute(
        sql_update(Bus)
        .where(Bus.id == data.bus_id)
        .values(status=BusStatus.on_route, driver_id=user.id)
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        sql_update(Driver)
        .where(Driver.driver_id == user.id)
        .values(is_online=True, status=DriverStatus.on_trip)
        .execution_options(synchronize_session=False)
    )

    await db.commit()
    return await _fetch_trip_out(db, trip.id)


@router.post("/{trip_id}/end", response_model=TripOut)
async def end_trip(trip_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    # Fetch only the columns we need — no ORM object, no selectin cascade
    row = (await db.execute(
        select(Trip.id, Trip.bus_id, Trip.driver_id, Trip.status)
        .where(Trip.id == trip_id, Trip.driver_id == user.id)
    )).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Trip not found")

    now = datetime.now(timezone.utc)

    await db.execute(
        sql_update(Trip)
        .where(Trip.id == trip_id)
        .values(status=TripStatus.completed, ended_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        sql_update(Bus)
        .where(Bus.id == row["bus_id"])
        .values(status=BusStatus.not_in_service, driver_id=None)
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        sql_update(Driver)
        .where(Driver.driver_id == user.id)
        .values(
            is_online=False,
            status=DriverStatus.available,
            total_trips=Driver.total_trips + 1,
        )
        .execution_options(synchronize_session=False)
    )

    await db.commit()
    return await _fetch_trip_out(db, trip_id)


@router.patch("/{trip_id}/status", response_model=TripOut)
async def update_trip_status(trip_id: UUID, data: TripStatusUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    row = (await db.execute(
        select(Trip.id, Trip.bus_id)
        .where(Trip.id == trip_id, Trip.driver_id == user.id)
    )).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Trip not found")

    await db.execute(
        sql_update(Trip)
        .where(Trip.id == trip_id)
        .values(status=data.status)
        .execution_options(synchronize_session=False)
    )

    status_map = {
        TripStatus.active:    BusStatus.on_route,
        TripStatus.cancelled: BusStatus.not_in_service,
    }
    bus_status = status_map.get(data.status)
    if bus_status is None and data.status.value == "delayed":
        bus_status = BusStatus.delayed
    if bus_status is not None:
        await db.execute(
            sql_update(Bus)
            .where(Bus.id == row["bus_id"])
            .values(status=bus_status)
            .execution_options(synchronize_session=False)
        )

    await db.commit()
    return await _fetch_trip_out(db, trip_id)


@router.patch("/{trip_id}/seats")
async def update_seats(trip_id: UUID, data: TripSeatUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    row = (await db.execute(
        select(Trip.id, Trip.bus_id)
        .where(Trip.id == trip_id, Trip.driver_id == user.id)
    )).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Get current bus capacity to clamp the value
    cap_row = (await db.execute(select(Bus.capacity).where(Bus.id == row["bus_id"]))).scalar_one_or_none()
    clamped = max(0, min(data.available_seats, cap_row or data.available_seats))

    await db.execute(
        sql_update(Bus)
        .where(Bus.id == row["bus_id"])
        .values(available_seats=clamped)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return {"message": "Seat availability updated", "available_seats": clamped}


@router.post("/{trip_id}/stops/{stop_id}/arrive")
async def mark_stop_arrival(trip_id: UUID, stop_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    exists = (await db.execute(
        select(Trip.id).where(Trip.id == trip_id, Trip.driver_id == user.id)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Arrival recorded", "trip_id": str(trip_id), "stop_id": str(stop_id)}


@router.get("/{trip_id}/eta", response_model=ETAResponse)
async def get_eta(trip_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    row = (await db.execute(
        select(Trip.id, Trip.bus_id).where(Trip.id == trip_id)
    )).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Trip not found")

    eta_data = await calculate_eta(db, row["bus_id"], trip_id)
    return eta_data


@router.get("/active", response_model=List[TripOut])
async def get_active_trips(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    rows = (await db.execute(
        select(
            Trip.id, Trip.driver_id, Trip.bus_id, Trip.route_id, Trip.status,
            Trip.started_at, Trip.ended_at, Trip.total_distance_km,
            Trip.total_passengers, Trip.created_at,
        ).where(Trip.status == TripStatus.active)
    )).mappings().all()
    return [TripOut(**dict(r)) for r in rows]