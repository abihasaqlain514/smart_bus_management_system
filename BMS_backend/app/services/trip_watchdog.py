"""
Trip Watchdog — auto-close timed-out trips
==========================================
Runs as an asyncio background task for the lifetime of the FastAPI process.

A trip is considered timed-out when:
    now  >  trip.started_at  +  scheduled_duration  +  OVERTIME_GRACE_HOURS

scheduled_duration is derived from the route's departure_time / arrival_time
strings (format "HH:MM").  Falls back to DEFAULT_TRIP_DURATION_H if those
fields are absent or unparseable.

Integration in main.py lifespan:
    asyncio.create_task(trip_watchdog_loop(db_factory=get_async_session))
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip, TripStatus
from app.models.route import Route

log = logging.getLogger(__name__)

OVERTIME_GRACE_HOURS    = 1       # how long past scheduled arrival before we close
DEFAULT_TRIP_DURATION_H = 1.5    # fallback if route times are missing
WATCHDOG_INTERVAL_S     = 300    # check every 5 minutes


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_hhmm(t: str | None) -> tuple[int, int] | None:
    """Parse "HH:MM" → (hour, minute).  Returns None on failure."""
    if not t:
        return None
    try:
        h, m = t.strip().split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        return None


def _route_duration_hours(route: Route) -> float:
    """
    Derive expected trip duration from route.departure_time / arrival_time.
    Falls back to DEFAULT_TRIP_DURATION_H.
    """
    dep = _parse_hhmm(getattr(route, "departure_time", None))
    arr = _parse_hhmm(getattr(route, "arrival_time",  None))
    if dep and arr:
        dep_min = dep[0] * 60 + dep[1]
        arr_min = arr[0] * 60 + arr[1]
        diff    = arr_min - dep_min
        if diff > 0:
            return diff / 60
    return DEFAULT_TRIP_DURATION_H


# ── core check ────────────────────────────────────────────────────────────────

async def close_timed_out_trips(db: AsyncSession) -> int:
    """
    Scan all active trips.  Close any whose deadline has passed.
    Returns the number of trips closed.
    """
    now = datetime.now(timezone.utc)

    rows = (
        await db.execute(
            select(Trip, Route)
            .join(Route, Trip.route_id == Route.id)
            .where(Trip.status == TripStatus.active)
        )
    ).all()

    closed = 0
    for trip, route in rows:
        if trip.started_at is None:
            continue

        duration_h = _route_duration_hours(route)
        deadline   = trip.started_at + timedelta(hours=duration_h + OVERTIME_GRACE_HOURS)

        if now > deadline:
            trip.status  = TripStatus.completed
            trip.ended_at = now
            await db.commit()

            log.warning(
                "watchdog: auto-closed trip %s (bus %s, route %s) — "
                "deadline was %s, now %s",
                trip.id, trip.bus_id, route.route_number,
                deadline.isoformat(), now.isoformat(),
            )
            closed += 1

    return closed


# ── background loop ───────────────────────────────────────────────────────────

async def trip_watchdog_loop(
    db_factory: Callable[[], AsyncGenerator],
    interval_seconds: int = WATCHDOG_INTERVAL_S,
) -> None:
    """
    Infinite loop — meant to be launched once via asyncio.create_task()
    inside FastAPI's lifespan.

    Example::
        # in main.py lifespan:
        asyncio.create_task(
            trip_watchdog_loop(db_factory=get_async_session),
            name="trip_watchdog",
        )
    """
    log.info("trip_watchdog started (interval=%ds)", interval_seconds)

    # Wait one interval before the first check so startup noise settles
    await asyncio.sleep(interval_seconds)

    while True:
        try:
            async with db_factory() as db:
                n = await close_timed_out_trips(db)
                if n:
                    log.info("trip_watchdog: closed %d timed-out trip(s)", n)
        except asyncio.CancelledError:
            log.info("trip_watchdog cancelled — shutting down")
            return
        except Exception as exc:
            # Never let a transient DB error kill the loop
            log.error("trip_watchdog error: %s", exc, exc_info=True)

        await asyncio.sleep(interval_seconds)
