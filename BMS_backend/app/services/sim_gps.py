"""
GPS Simulation Service
======================
Moves a virtual bus along a list of (lat, lng) waypoints at a given speed,
writing BusLocation rows and broadcasting via WebSocket on every tick.

Usage (from an async context):
    task = asyncio.create_task(
        simulate_trip(bus_id, trip_id, waypoints, db_factory=get_async_session)
    )
    # cancel whenever needed:
    task.cancel()
"""

import asyncio
import logging
import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bus_location import BusLocation
from app.models.trip import Trip, TripStatus
from app.websockets.manager import connection_manager

log = logging.getLogger(__name__)

# ── Registry of running simulation tasks (bus_id → asyncio.Task) ─────────────
_running: dict[str, asyncio.Task] = {}


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in km between two (lat, lng) points."""
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Forward azimuth (0–360°) from point a to point b."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _lerp(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    """Linear interpolation between two GPS points (t in [0, 1])."""
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _position_at_km(
    segments: list[dict],
    target_km: float,
) -> tuple[float, float, float]:
    """
    Given a list of pre-computed segments and a cumulative distance target,
    return (lat, lng, heading_deg) of the interpolated position.
    """
    cum = 0.0
    for seg in segments:
        if target_km <= cum + seg["dist"]:
            frac = (target_km - cum) / seg["dist"] if seg["dist"] > 0 else 0.0
            lat, lng = _lerp(seg["start"], seg["end"], frac)
            return lat, lng, seg["hdg"]
        cum += seg["dist"]
    # Past the end — return final point
    last = segments[-1]
    return last["end"][0], last["end"][1], last["hdg"]


# ── Core simulation coroutine ─────────────────────────────────────────────────

async def simulate_trip(
    bus_id: str | UUID,
    trip_id: str | UUID,
    waypoints: list[tuple[float, float]],
    speed_kmh: float = 35.0,
    tick_seconds: float = 3.0,
    db_factory: Callable[[], AsyncGenerator] = None,
) -> None:
    """
    Simulate a moving bus along *waypoints* at *speed_kmh*.

    Every *tick_seconds* seconds:
      1. Compute interpolated (lat, lng, heading).
      2. Persist a BusLocation row.
      3. Broadcast via WebSocket so passengers see live movement.

    The coroutine exits naturally when the bus reaches the last waypoint,
    or is cancelled externally (trip ended / watchdog / error).
    """
    bus_id  = str(bus_id)
    trip_id = str(trip_id)

    if len(waypoints) < 2:
        log.warning("sim_gps: need at least 2 waypoints — aborting")
        return

    # Pre-build segment table
    segments = []
    for i in range(len(waypoints) - 1):
        d = _haversine_km(waypoints[i], waypoints[i + 1])
        segments.append({
            "start": waypoints[i],
            "end":   waypoints[i + 1],
            "dist":  max(d, 1e-9),          # avoid /0
            "hdg":   _bearing(waypoints[i], waypoints[i + 1]),
        })

    total_km       = sum(s["dist"] for s in segments)
    total_seconds  = (total_km / speed_kmh) * 3600
    ticks          = math.ceil(total_seconds / tick_seconds)
    step_km        = (speed_kmh / 3600) * tick_seconds   # km covered per tick

    log.info(
        "sim_gps START bus=%s trip=%s route=%.2f km speed=%.0f km/h "
        "~%.0f s (%d ticks)",
        bus_id, trip_id, total_km, speed_kmh, total_seconds, ticks,
    )

    covered_km = 0.0

    try:
        while covered_km <= total_km:
            lat, lng, hdg = _position_at_km(segments, covered_km)

            # ── 1. Persist GPS row ─────────────────────────────────────────
            if db_factory:
                async with db_factory() as db:
                    loc = BusLocation(
                        bus_id     = bus_id,
                        trip_id    = trip_id,
                        latitude   = round(lat, 7),
                        longitude  = round(lng, 7),
                        speed_kmh  = round(speed_kmh, 2),
                        heading_deg= round(hdg, 1),
                    )
                    db.add(loc)
                    await db.commit()

            # ── 2. Broadcast via WebSocket ─────────────────────────────────
            payload = {
                "bus_id"    : bus_id,
                "trip_id"   : trip_id,
                "latitude"  : round(lat, 7),
                "longitude" : round(lng, 7),
                "speed_kmh" : round(speed_kmh, 2),
                "heading_deg": round(hdg, 1),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "simulated" : True,
            }
            await connection_manager.broadcast_to_bus(bus_id, payload)

            covered_km += step_km
            await asyncio.sleep(tick_seconds)

    except asyncio.CancelledError:
        log.info("sim_gps CANCELLED bus=%s trip=%s", bus_id, trip_id)
        raise
    finally:
        _running.pop(bus_id, None)

    log.info("sim_gps DONE bus=%s trip=%s", bus_id, trip_id)


# ── Public control API ────────────────────────────────────────────────────────

def start_simulation(
    bus_id: str,
    trip_id: str,
    waypoints: list[tuple[float, float]],
    speed_kmh: float = 35.0,
    tick_seconds: float = 3.0,
    db_factory=None,
) -> asyncio.Task:
    """
    Start (or restart) a GPS simulation for *bus_id*.
    Returns the asyncio.Task so callers can await or cancel it.
    """
    stop_simulation(bus_id)          # cancel any previous run for this bus

    task = asyncio.create_task(
        simulate_trip(bus_id, trip_id, waypoints, speed_kmh, tick_seconds, db_factory),
        name=f"sim_gps:{bus_id}",
    )
    _running[bus_id] = task
    return task


def stop_simulation(bus_id: str) -> bool:
    """Cancel a running simulation.  Returns True if one was running."""
    task = _running.pop(bus_id, None)
    if task and not task.done():
        task.cancel()
        return True
    return False


def active_simulations() -> list[str]:
    """Return bus_ids currently being simulated."""
    return list(_running.keys())


# ── Jhang route waypoints (reusable presets) ──────────────────────────────────

JHANG_ROUTES: dict[str, list[tuple[float, float]]] = {
    "1-M": [   # Chiniot → University of Jhang
        (31.7200, 72.9800),   # Chiniot City Centre
        (31.6800, 72.9200),   # Chiniot bypass
        (31.6200, 72.8100),   # Rabwah junction
        (31.5600, 72.6900),   # Faisalabad Road
        (31.4800, 72.5400),   # Shah Jewana
        (31.3900, 72.4300),   # Jhang city entry
        (31.3100, 72.3800),   # Jhang Saddar
        (31.2693, 72.3210),   # University of Jhang ✓
    ],
    "2-M": [   # Toba Tek Singh → University of Jhang
        (30.9700, 72.4800),   # TTS City
        (31.0500, 72.4200),   # TTS bypass
        (31.1400, 72.3900),   # Kamalia road junction
        (31.2100, 72.3600),   # Jhang outskirts
        (31.2500, 72.3400),   # Jhang Saddar
        (31.2693, 72.3210),   # University of Jhang ✓
    ],
    "city_loop": [  # Short loop around Jhang city centre — good for demo
        (31.2693, 72.3210),
        (31.2750, 72.3300),
        (31.2820, 72.3380),
        (31.2900, 72.3290),
        (31.2860, 72.3150),
        (31.2780, 72.3080),
        (31.2693, 72.3210),  # back to university
    ],
}
