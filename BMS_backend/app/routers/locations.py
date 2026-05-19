from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.deps import require_driver, get_current_user
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.schemas.location import LocationUpdate, LocationOut, LiveBusOut, NearestStopOut
from app.services.gps_service import get_latest_bus_location, get_nearest_stops
from app.websockets.manager import connection_manager

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("/update", response_model=LocationOut)
async def post_location(
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_driver),
):
    location = BusLocation(
        bus_id=data.bus_id,
        trip_id=data.trip_id,
        latitude=data.latitude,
        longitude=data.longitude,
        speed_kmh=data.speed_kmh,
        heading_deg=data.heading_deg,
    )
    db.add(location)

    if data.available_seats is not None:
        bus_result = await db.execute(select(Bus).where(Bus.id == data.bus_id))
        bus = bus_result.scalar_one_or_none()
        if bus:
            bus.available_seats = max(0, min(data.available_seats, bus.capacity))

    await db.commit()
    await db.refresh(location)

    payload = {
        "bus_id": str(data.bus_id),
        "latitude": float(data.latitude),
        "longitude": float(data.longitude),
        "speed_kmh": float(data.speed_kmh) if data.speed_kmh else None,
        "heading_deg": float(data.heading_deg) if data.heading_deg else None,
        "recorded_at": location.recorded_at.isoformat(),
    }
    await connection_manager.broadcast_to_bus(str(data.bus_id), payload)
    return location


@router.get("/live", response_model=List[LiveBusOut])
async def live_buses(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Bus).where(Bus.is_active == True))
    buses = result.scalars().all()

    live = []
    for bus in buses:
        loc = await get_latest_bus_location(db, bus.id)
        live.append(LiveBusOut(
            bus_id=bus.id,
            bus_number=bus.bus_number,
            status=bus.status.value,
            available_seats=bus.available_seats,
            capacity=bus.capacity,                          # ← was missing
            latitude=loc.latitude if loc else None,
            longitude=loc.longitude if loc else None,
            speed_kmh=loc.speed_kmh if loc else None,
            heading_deg=loc.heading_deg if loc else None,
            recorded_at=loc.recorded_at if loc else None,
            driver_name=bus.current_driver.user.full_name if bus.current_driver and bus.current_driver.user else None,
            driver_code=bus.current_driver.driver_code if bus.current_driver else None,
            route_id=bus.route_id,
            route_name=bus.route.route_name if bus.route else None,
            route_number=bus.route.route_number if bus.route else None,
            active_trip_id=next(
                (str(t.id) for t in bus.trips if t.status.value == "active"), None
            ) if bus.trips else None,
        ))
    return live


@router.get("/nearest", response_model=List[NearestStopOut])
async def nearest_stops(
    lat: float = Query(..., description="Your latitude, e.g. 31.5204"),
    lng: float = Query(..., description="Your longitude, e.g. 74.3587"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    stops_with_distances = await get_nearest_stops(db, lat, lng)
    return [
        NearestStopOut(
            stop_id=stop.id,
            stop_name=stop.stop_name,
            stop_order=stop.stop_order,                                          # ← was missing
            route_id=stop.route_id,
            route_name=stop.route.route_name if stop.route else "",
            route_number=stop.route.route_number if stop.route else "",          # ← was missing
            latitude=stop.latitude,
            longitude=stop.longitude,
            distance_km=round(dist, 3),
            estimated_minutes=stop.estimated_minutes,
        )
        for stop, dist in stops_with_distances
    ]


@router.websocket("/ws/live-tracking")
async def websocket_live_tracking(
    websocket: WebSocket,
    bus_id: Optional[str] = Query(None, description="Subscribe to a specific bus UUID, or omit for all buses"),
):
    await connection_manager.connect(websocket, bus_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, bus_id)
