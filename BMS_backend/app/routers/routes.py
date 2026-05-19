from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.deps import require_admin, get_current_user
from app.models.route import Route, Stop
from app.models.bus import Bus
from app.schemas.route import RouteCreate, RouteUpdate, RouteOut, StopCreate, StopOut, StopUpdate

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/", response_model=List[RouteOut])
async def list_routes(
    search: Optional[str] = Query(None, description="Search by route name, number, or stop name"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Returns all active routes with their stops.
    Optional ?search= filters by route name, route number, or any stop name.
    """
    result = await db.execute(
        select(Route).where(Route.is_active == True)
    )
    routes = result.scalars().all()

    if not search:
        return routes

    # Client-side filter so we keep the full Route ORM objects (with stops loaded)
    q = search.strip().lower()
    filtered = []
    for r in routes:
        if (q in r.route_name.lower() or
            q in r.route_number.lower() or
            q in r.start_point.lower() or
            q in r.end_point.lower() or
            any(q in s.stop_name.lower() for s in r.stops)):
            filtered.append(r)
    return filtered


@router.get("/{route_id}", response_model=RouteOut)
async def get_route(route_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/{route_id}/buses")
async def get_route_buses(route_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Returns all active buses on a route with their current trip & driver status."""
    from app.models.trip import Trip, TripStatus
    from app.models.driver import Driver
    from app.models.user import User

    buses = (await db.execute(
        select(Bus.id, Bus.bus_number, Bus.available_seats, Bus.capacity, Bus.status, Bus.model)
        .where(Bus.route_id == route_id, Bus.is_active == True)
    )).mappings().all()

    result = []
    for b in buses:
        trip = (await db.execute(
            select(Trip.id, Trip.driver_id, Trip.started_at, Trip.total_passengers)
            .where(Trip.bus_id == b["id"], Trip.status == TripStatus.active)
        )).mappings().one_or_none()

        driver_name = driver_code = started_at = trip_id = None
        total_passengers = 0
        if trip:
            trip_id = trip["id"]
            started_at = trip["started_at"].isoformat() if trip["started_at"] else None
            total_passengers = trip["total_passengers"] or 0
            drv = (await db.execute(
                select(User.full_name, Driver.driver_code)
                .join(Driver, Driver.driver_id == User.id)
                .where(Driver.driver_id == trip["driver_id"])
            )).mappings().one_or_none()
            if drv:
                driver_name = drv["full_name"]
                driver_code = drv["driver_code"]

        result.append({
            "bus_id":           str(b["id"]),
            "bus_number":       b["bus_number"],
            "bus_model":        b["model"],
            "available_seats":  b["available_seats"],
            "capacity":         b["capacity"],
            "bus_status":       b["status"].value if b["status"] else "not_in_service",
            "active_trip_id":   str(trip_id) if trip_id else None,
            "driver_name":      driver_name,
            "driver_code":      driver_code,
            "started_at":       started_at,
            "total_passengers": total_passengers,
        })
    return result


@router.get("/{route_id}/stops", response_model=List[StopOut])
async def get_route_stops(route_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Stop).where(Stop.route_id == route_id).order_by(Stop.stop_order)
    )
    return result.scalars().all()


@router.post("/", response_model=RouteOut)
async def create_route(data: RouteCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    existing = await db.execute(select(Route).where(Route.route_number == data.route_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Route number already exists")

    route = Route(**data.model_dump())
    db.add(route)
    await db.commit()
    await db.refresh(route)

    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="CREATE_ROUTE",
        table_name="routes",
        record_id=str(route.id),
        new_value=data.model_dump(),
    ))
    await db.commit()
    return route


@router.post("/{route_id}/stops", response_model=StopOut)
async def add_stop(route_id: UUID, data: StopCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route not found")

    stop = Stop(route_id=route_id, **data.model_dump())
    db.add(stop)
    await db.commit()
    await db.refresh(stop)
    return stop


@router.put("/{route_id}", response_model=RouteOut)
async def update_route(route_id: UUID, data: RouteUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(route, field, value)

    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="UPDATE_ROUTE",
        table_name="routes",
        record_id=str(route_id),
        new_value=data.model_dump(exclude_none=True),
    ))
    await db.commit()
    await db.refresh(route)
    return route


@router.put("/{route_id}/stops/{stop_id}", response_model=StopOut)
async def update_stop(
    route_id: UUID, stop_id: UUID, data: StopUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    stop = (await db.execute(
        select(Stop).where(Stop.id == stop_id, Stop.route_id == route_id)
    )).scalar_one_or_none()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(stop, field, value)
    await db.commit()
    await db.refresh(stop)
    return stop


@router.delete("/{route_id}/stops/{stop_id}")
async def delete_stop(
    route_id: UUID, stop_id: UUID,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    stop = (await db.execute(
        select(Stop).where(Stop.id == stop_id, Stop.route_id == route_id)
    )).scalar_one_or_none()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    await db.delete(stop)
    await db.commit()
    return {"message": "Stop deleted"}


@router.delete("/{route_id}")
async def delete_route(route_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.is_active = False
    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="DELETE_ROUTE",
        table_name="routes",
        record_id=str(route_id),
    ))
    await db.commit()
    return {"message": "Route deactivated"}
