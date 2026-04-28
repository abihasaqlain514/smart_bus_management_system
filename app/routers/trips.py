from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps import require_driver, get_current_user
from app.models.trip import Trip, TripStatus
from app.models.bus import Bus, BusStatus
from app.models.driver import Driver, DriverStatus
from app.schemas.trip import TripStart, TripStatusUpdate, TripSeatUpdate, TripOut, ETAResponse
from app.services.gps_service import calculate_eta
from app.websockets.manager import connection_manager

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/start", response_model=TripOut)
async def start_trip(data: TripStart, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    driver_result = await db.execute(select(Driver).where(Driver.driver_id == user.id))
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    bus_result = await db.execute(select(Bus).where(Bus.id == data.bus_id, Bus.is_active == True))
    bus = bus_result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    trip = Trip(
        driver_id=user.id,
        bus_id=data.bus_id,
        route_id=data.route_id,
        status=TripStatus.active,
    )
    db.add(trip)

    bus.status = BusStatus.on_route
    bus.driver_id = user.id
    driver.is_online = True
    driver.status = DriverStatus.on_trip

    await db.commit()
    await db.refresh(trip)
    return trip


@router.post("/{trip_id}/end", response_model=TripOut)
async def end_trip(trip_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    now = datetime.now(timezone.utc)
    trip.status = TripStatus.completed
    trip.ended_at = now

    bus_result = await db.execute(select(Bus).where(Bus.id == trip.bus_id))
    bus = bus_result.scalar_one_or_none()
    if bus:
        bus.status = BusStatus.not_in_service
        bus.driver_id = None

    driver_result = await db.execute(select(Driver).where(Driver.driver_id == user.id))
    driver = driver_result.scalar_one_or_none()
    if driver:
        driver.is_online = False
        driver.status = DriverStatus.available
        driver.total_trips = (driver.total_trips or 0) + 1

    await db.commit()
    await db.refresh(trip)
    return trip


@router.patch("/{trip_id}/status", response_model=TripOut)
async def update_trip_status(trip_id: UUID, data: TripStatusUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip.status = data.status

    # Mirror status on bus
    bus_result = await db.execute(select(Bus).where(Bus.id == trip.bus_id))
    bus = bus_result.scalar_one_or_none()
    if bus:
        status_map = {
            TripStatus.active: BusStatus.on_route,
            TripStatus.cancelled: BusStatus.not_in_service,
        }
        if data.status in status_map:
            bus.status = status_map[data.status]
        elif data.status.value == "delayed":
            bus.status = BusStatus.delayed

    await db.commit()
    await db.refresh(trip)
    return trip


@router.patch("/{trip_id}/seats")
async def update_seats(trip_id: UUID, data: TripSeatUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    bus_result = await db.execute(select(Bus).where(Bus.id == trip.bus_id))
    bus = bus_result.scalar_one_or_none()
    if bus:
        bus.available_seats = max(0, min(data.available_seats, bus.capacity))

    await db.commit()
    return {"message": "Seat availability updated", "available_seats": bus.available_seats if bus else data.available_seats}


@router.post("/{trip_id}/stops/{stop_id}/arrive")
async def mark_stop_arrival(trip_id: UUID, stop_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_driver)):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.driver_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return {"message": "Arrival recorded", "trip_id": str(trip_id), "stop_id": str(stop_id)}


@router.get("/{trip_id}/eta", response_model=ETAResponse)
async def get_eta(trip_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    eta_data = await calculate_eta(db, trip.bus_id, trip_id)
    return eta_data


@router.get("/active", response_model=List[TripOut])
async def get_active_trips(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Trip).where(Trip.status == TripStatus.active))
    return result.scalars().all()
