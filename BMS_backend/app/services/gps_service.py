import math
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.bus_location import BusLocation
from app.models.trip import Trip
from app.models.route import Stop


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in km between two GPS coordinates (Haversine formula)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_latest_bus_location(db: AsyncSession, bus_id: UUID) -> Optional[BusLocation]:
    result = await db.execute(
        select(BusLocation)
        .where(BusLocation.bus_id == bus_id)
        .order_by(desc(BusLocation.recorded_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def calculate_eta(db: AsyncSession, bus_id: UUID, trip_id: UUID) -> dict:
    """
    Calculate ETA to the nearest upcoming stop.
    Returns a dict whose keys exactly match ETAResponse field names.
    """
    base = {"trip_id": trip_id, "bus_id": bus_id}

    location = await get_latest_bus_location(db, bus_id)
    if not location:
        return base

    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        return base

    stops_result = await db.execute(
        select(Stop)
        .where(Stop.route_id == trip.route_id)
        .order_by(Stop.stop_order)
    )
    stops = stops_result.scalars().all()
    if not stops:
        return base

    bus_lat = float(location.latitude)
    bus_lng = float(location.longitude)
    speed = float(location.speed_kmh) if location.speed_kmh else 30.0

    nearest_stop = min(
        stops,
        key=lambda s: haversine_distance(bus_lat, bus_lng, float(s.latitude), float(s.longitude)),
    )
    distance = haversine_distance(bus_lat, bus_lng, float(nearest_stop.latitude), float(nearest_stop.longitude))
    eta_minutes = int((distance / speed) * 60) if speed > 0 else None

    return {
        **base,
        "next_stop_id": nearest_stop.id,
        "next_stop_name": nearest_stop.stop_name,
        "distance_to_stop_km": round(distance, 2),
        "estimated_minutes": eta_minutes,
        "current_speed_kmh": speed,
        "current_latitude": bus_lat,
        "current_longitude": bus_lng,
    }


async def get_nearest_stops(db: AsyncSession, user_lat: float, user_lng: float, limit: int = 5) -> list:
    """Return stops sorted by distance from user coordinates."""
    result = await db.execute(select(Stop))
    all_stops = result.scalars().all()

    stops_with_distance = sorted(
        [(stop, haversine_distance(user_lat, user_lng, float(stop.latitude), float(stop.longitude)))
         for stop in all_stops],
        key=lambda x: x[1],
    )
    return stops_with_distance[:limit]
