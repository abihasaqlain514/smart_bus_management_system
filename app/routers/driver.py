from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.deps import require_driver
from app.models.driver import Driver
from app.models.issue_report import IssueReport
from app.schemas.driver import DriverOut
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
        assigned_bus_id=driver.assigned_bus_id,
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
