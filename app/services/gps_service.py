import math
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.bus_location import BusLocation
from app.models.trip import Trip
from app.models.route import Stop


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in km between two GPS coordinates using the Haversine formula."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def get_latest_bus_location(db: AsyncSession, bus_id: UUID) -> Optional[BusLocation]:
    result = await db.execute(
        select(BusLocation)
        .where(BusLocation.bus_id == bus_id)
        .order_by(desc(BusLocation.recorded_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def calculate_eta(db: AsyncSession, bus_id: UUID, trip_id: UUID) -> dict:
    """Calculate ETA to the next stop using the latest GPS fix and Haversine formula."""
    location = await get_latest_bus_location(db, bus_id)
    if not location:
        return {}

    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        return {}

    # Find stops on this route ordered by stop_order
    stops_result = await db.execute(
        select(Stop)
        .where(Stop.route_id == trip.route_id)
        .order_by(Stop.stop_order)
    )
    stops = stops_result.scalars().all()
    if not stops:
        return {}

    bus_lat = float(location.latitude)
    bus_lng = float(location.longitude)
    speed = float(location.speed_kmh) if location.speed_kmh else 30.0

    # Find the nearest upcoming stop (closest by distance)
    nearest_stop = None
    min_distance = float("inf")
    for stop in stops:
        d = haversine_distance(bus_lat, bus_lng, float(stop.latitude), float(stop.longitude))
        if d < min_distance:
            min_distance = d
            nearest_stop = stop

    if not nearest_stop:
        return {}

    eta_minutes = int((min_distance / speed) * 60) if speed > 0 else None

    return {
        "next_stop": nearest_stop.stop_name,
        "distance_km": round(min_distance, 2),
        "estimated_minutes": eta_minutes,
        "current_speed_kmh": speed,
    }


async def get_nearest_stops(db: AsyncSession, user_lat: float, user_lng: float, limit: int = 5) -> list:
    """Return stops sorted by distance from user coordinates."""
    result = await db.execute(select(Stop))
    all_stops = result.scalars().all()

    stops_with_distance = []
    for stop in all_stops:
        d = haversine_distance(user_lat, user_lng, float(stop.latitude), float(stop.longitude))
        stops_with_distance.append((stop, d))

    stops_with_distance.sort(key=lambda x: x[1])
    return stops_with_distance[:limit]
