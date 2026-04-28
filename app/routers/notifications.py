from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps import require_driver, require_admin, require_passenger, get_current_user
from app.models.notification import Notification, NotificationType
from app.models.trip import Trip
from app.schemas.notification import NotificationSend, BroadcastNotification, NotificationOut
from app.services.notification_service import (
    create_notification,
    broadcast_notification,
    notify_route_passengers,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send")
async def send_notification(
    data: NotificationSend,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_driver),
):
    if data.trip_id:
        trip_result = await db.execute(
            select(Trip).where(Trip.id == data.trip_id, Trip.driver_id == user.id)
        )
        trip = trip_result.scalar_one_or_none()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found or not yours")

        count = await notify_route_passengers(
            db,
            route_id=trip.route_id,
            notification_type=data.type,
            title=data.title,
            message=data.message,
            trip_id=data.trip_id,
        )
        return {"message": f"Notification sent to {count} passengers"}

    return {"message": "No recipients — provide trip_id"}


@router.post("/broadcast")
async def broadcast(data: BroadcastNotification, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    count = await broadcast_notification(db, data.title, data.message, data.target_role)
    return {"message": f"Broadcast sent to {count} users"}


@router.get("/my", response_model=List[NotificationOut])
async def my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}
