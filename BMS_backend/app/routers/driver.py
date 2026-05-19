from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.deps import require_driver
from app.models.driver import Driver
from app.models.bus import Bus
from app.models.route import Route
from app.models.trip import Trip, TripStatus
from app.models.issue_report import IssueReport
from app.schemas.driver import DriverOut
from app.schemas.trip import TripOut
from app.schemas.issue_report import IssueReportCreate, IssueReportOut
from app.services.notification_service import notify_route_passengers
from app.models.notification import NotificationType

router = APIRouter(prefix="/driver", tags=["driver"])


@router.get("/profile", response_model=DriverOut)
async def get_driver_profile(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_driver),
):
    result = await db.execute(select(Driver).where(Driver.driver_id == user.id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    bus_number = None
    bus_route_id = None
    route_name = None
    active_bus_id = None   # only set when the assigned bus is actually active

    if driver.assigned_bus_id:
        # Only expose the bus if it is active — avoids "Bus not found" on trip start
        bus_res = await db.execute(
            select(Bus).where(Bus.id == driver.assigned_bus_id, Bus.is_active == True)
        )
        bus = bus_res.scalar_one_or_none()
        if bus:
            active_bus_id = driver.assigned_bus_id
            bus_number = bus.bus_number
            bus_route_id = bus.route_id
            if bus.route_id:
                route_res = await db.execute(select(Route).where(Route.id == bus.route_id))
                route = route_res.scalar_one_or_none()
                if route:
                    route_name = route.route_name

    return DriverOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        is_active=user.is_active,
        created_at=user.created_at,
        driver_id=driver.driver_id,
        driver_code=driver.driver_code,
        license_number=driver.license_number,
        assigned_bus_id=active_bus_id,   # None when bus is deactivated
        bus_number=bus_number,
        bus_route_id=bus_route_id,
        route_name=route_name,
        is_online=driver.is_online,
        status=driver.status,
        avg_rating=driver.avg_rating,
        total_trips=driver.total_trips,
    )


@router.post("/issues", response_model=IssueReportOut, status_code=201)
async def report_issue(
    data: IssueReportCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_driver),
):
    from app.models.trip import Trip

    trip_result = await db.execute(
        select(Trip).where(Trip.id == data.trip_id, Trip.driver_id == user.id)
    )
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or does not belong to you")

    issue = IssueReport(
        trip_id=data.trip_id,
        driver_id=user.id,
        issue_type=data.issue_type,
        description=data.description,
        severity=data.severity,
    )
    db.add(issue)
    await db.flush()

    # Notify passengers (and their parents) on this route for high/critical issues
    if data.severity.value in ("critical", "high"):
        await notify_route_passengers(
            db,
            route_id=trip.route_id,
            notification_type=NotificationType.emergency,
            title=f"Bus Issue: {data.issue_type.value.title()}",
            message=data.description or f"A {data.severity.value} issue has been reported on your route.",
            trip_id=trip.id,
        )

    await db.commit()
    await db.refresh(issue)
    return issue


@router.get("/active-trip", response_model=Optional[TripOut])
async def get_my_active_trip(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_driver),
):
    """Returns this driver's current active trip, or null if none."""
    row = (await db.execute(
        select(
            Trip.id, Trip.driver_id, Trip.bus_id, Trip.route_id, Trip.status,
            Trip.started_at, Trip.ended_at, Trip.total_distance_km,
            Trip.total_passengers, Trip.created_at,
        ).where(Trip.driver_id == user.id, Trip.status == TripStatus.active)
    )).mappings().one_or_none()

    if row is None:
        return None
    return TripOut(**dict(row))
