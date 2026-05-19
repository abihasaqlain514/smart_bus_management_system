"""
Debug / Simulation Router
=========================
Only active in development.  Provides HTTP endpoints to:

  POST   /api/debug/simulate/{trip_id}   — start GPS simulation for a trip
  DELETE /api/debug/simulate/{trip_id}   — stop  GPS simulation for a trip
  GET    /api/debug/simulate             — list  active simulations
  POST   /api/debug/watchdog/run         — manually trigger the trip watchdog

All endpoints are protected by admin JWT so they are not publicly accessible.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models.bus import Bus
from app.models.route import Stop
from app.models.trip import Trip, TripStatus
from app.services import sim_gps, trip_watchdog
from app.database import AsyncSessionLocal           # raw factory for bg tasks

log = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug / Simulation"])


# ── request schema ────────────────────────────────────────────────────────────

class SimRequest(BaseModel):
    speed_kmh:    float = 35.0
    tick_seconds: float = 3.0
    # Optional: override waypoints (list of [lat, lng] pairs).
    # If omitted, waypoints are pulled from the trip's route stops.
    waypoints: list[list[float]] | None = None


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/simulate/{trip_id}", summary="Start GPS simulation for a trip")
async def start_sim(
    trip_id: UUID,
    body:    SimRequest = SimRequest(),
    db:      AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """
    Starts a background coroutine that moves the trip's bus along the route
    stops, posting BusLocation rows and broadcasting via WebSocket every
    `tick_seconds` seconds.

    If the trip is already being simulated it is restarted.
    """
    # Validate trip exists and is active
    trip_row = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_row.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")
    if trip.status != TripStatus.active:
        raise HTTPException(400, f"Trip is '{trip.status.value}' — must be active to simulate")

    # Build waypoints: prefer user-supplied, fall back to route stops
    if body.waypoints:
        waypoints = [tuple(p) for p in body.waypoints]
    else:
        stops_row = await db.execute(
            select(Stop)
            .where(Stop.route_id == trip.route_id)
            .order_by(Stop.stop_order)
        )
        stops = stops_row.scalars().all()
        if len(stops) < 2:
            raise HTTPException(400, "Route has fewer than 2 stops — cannot simulate")
        waypoints = [(float(s.latitude), float(s.longitude)) for s in stops]

    sim_gps.start_simulation(
        bus_id       = str(trip.bus_id),
        trip_id      = str(trip.id),
        waypoints    = waypoints,
        speed_kmh    = body.speed_kmh,
        tick_seconds = body.tick_seconds,
        db_factory   = AsyncSessionLocal,
    )

    log.info("Simulation started: trip=%s bus=%s waypoints=%d speed=%.0f",
             trip_id, trip.bus_id, len(waypoints), body.speed_kmh)

    return {
        "status":    "simulation_started",
        "trip_id":   str(trip_id),
        "bus_id":    str(trip.bus_id),
        "waypoints": len(waypoints),
        "speed_kmh": body.speed_kmh,
        "tick_s":    body.tick_seconds,
        "note":      "Subscribe to WS /api/locations/ws/live-tracking?bus_id=<bus_id>",
    }


@router.delete("/simulate/{trip_id}", summary="Stop GPS simulation for a trip")
async def stop_sim(
    trip_id: UUID,
    db:      AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """Cancel a running simulation for this trip's bus."""
    trip_row = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_row.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")

    stopped = sim_gps.stop_simulation(str(trip.bus_id))
    return {"status": "stopped" if stopped else "not_running", "bus_id": str(trip.bus_id)}


@router.get("/simulate", summary="List active simulations")
async def list_sims(_admin = Depends(require_admin)):
    return {"active_bus_ids": sim_gps.active_simulations()}


@router.post("/watchdog/run", summary="Manually trigger the trip timeout watchdog")
async def run_watchdog(
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """Immediately runs the watchdog check (useful for testing timeout logic)."""
    closed = await trip_watchdog.close_timed_out_trips(db)
    return {"trips_auto_closed": closed}


@router.post(
    "/simulate/preset/{route_name}",
    summary="Start simulation using a built-in Jhang route preset",
)
async def start_preset_sim(
    route_name: str,
    trip_id:    UUID = Query(..., description="Active trip UUID to simulate"),
    speed_kmh:  float = Query(35.0),
    tick_s:     float = Query(3.0),
    db:         AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """
    Use one of the pre-defined Jhang routes from sim_gps.JHANG_ROUTES.
    Handy for quick demos without needing a real route in the DB.

    Available presets: 1-M, 2-M, city_loop
    """
    waypoints = sim_gps.JHANG_ROUTES.get(route_name)
    if not waypoints:
        raise HTTPException(
            400,
            f"Unknown preset '{route_name}'. "
            f"Available: {list(sim_gps.JHANG_ROUTES.keys())}",
        )

    trip_row = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_row.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")
    if trip.status != TripStatus.active:
        raise HTTPException(400, "Trip must be active")

    sim_gps.start_simulation(
        bus_id=str(trip.bus_id), trip_id=str(trip.id),
        waypoints=waypoints, speed_kmh=speed_kmh,
        tick_seconds=tick_s, db_factory=AsyncSessionLocal,
    )

    return {
        "status": "simulation_started",
        "preset": route_name,
        "waypoints": len(waypoints),
        "speed_kmh": speed_kmh,
    }
