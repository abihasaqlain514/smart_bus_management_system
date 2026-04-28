from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole


async def create_notification(
    db: AsyncSession,
    recipient_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    trip_id: Optional[UUID] = None,
    send_fcm: bool = False,
) -> Notification:
    notification = Notification(
        recipient_id=recipient_id,
        trip_id=trip_id,
        type=notification_type,
        title=title,
        message=message,
        sent_via_fcm=False,
    )
    db.add(notification)

    if send_fcm:
        # Attempt to push via Firebase if recipient has an FCM token
        result = await db.execute(select(User).where(User.id == recipient_id))
        user = result.scalar_one_or_none()
        if user and user.fcm_token:
            fcm_sent = await _send_fcm(user.fcm_token, title, message)
            notification.sent_via_fcm = fcm_sent

    await db.commit()
    await db.refresh(notification)
    return notification


async def broadcast_notification(
    db: AsyncSession,
    title: str,
    message: str,
    target_role: Optional[str] = None,
) -> int:
    """Send a notification to all active users (or a specific role). Returns count sent."""
    query = select(User).where(User.is_active == True)
    if target_role:
        query = query.where(User.role == target_role)

    result = await db.execute(query)
    users = result.scalars().all()

    notifications = [
        Notification(
            recipient_id=user.id,
            type=NotificationType.broadcast,
            title=title,
            message=message,
        )
        for user in users
    ]
    db.add_all(notifications)
    await db.commit()
    return len(notifications)


async def notify_route_passengers(
    db: AsyncSession,
    route_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    trip_id: Optional[UUID] = None,
) -> int:
    """
    Notify all passengers on a specific route AND the parents of those
    passengers, so parents receive the same emergency/delay/arrival alerts.
    """
    from app.models.passenger import Passenger
    from app.models.parent import ParentChild

    result = await db.execute(
        select(Passenger).where(Passenger.preferred_route_id == route_id)
    )
    passengers = result.scalars().all()
    passenger_ids = [p.passenger_id for p in passengers]

    notifications: list[Notification] = [
        Notification(
            recipient_id=p.passenger_id,
            trip_id=trip_id,
            type=notification_type,
            title=title,
            message=message,
        )
        for p in passengers
    ]

    # Also notify all parents linked to these passengers
    if passenger_ids:
        parent_links_result = await db.execute(
            select(ParentChild).where(ParentChild.child_id.in_(passenger_ids))
        )
        parent_links = parent_links_result.scalars().all()

        # Deduplicate: a parent might be linked to multiple children on the route
        notified_parents: set[UUID] = set()
        for link in parent_links:
            if link.parent_id not in notified_parents:
                notifications.append(
                    Notification(
                        recipient_id=link.parent_id,
                        trip_id=trip_id,
                        type=notification_type,
                        title=title,
                        message=f"[Your child's bus] {message}",
                    )
                )
                notified_parents.add(link.parent_id)

    db.add_all(notifications)
    await db.commit()
    return len(notifications)


async def notify_parents_of_passenger(
    db: AsyncSession,
    passenger_id: UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    trip_id: Optional[UUID] = None,
) -> int:
    """Send a notification to all parents linked to a specific passenger."""
    from app.models.parent import ParentChild

    result = await db.execute(
        select(ParentChild).where(ParentChild.child_id == passenger_id)
    )
    links = result.scalars().all()

    notifications = [
        Notification(
            recipient_id=link.parent_id,
            trip_id=trip_id,
            type=notification_type,
            title=title,
            message=f"[Your child's bus] {message}",
        )
        for link in links
    ]
    db.add_all(notifications)
    await db.commit()
    return len(notifications)


async def _send_fcm(token: str, title: str, body: str) -> bool:
    """Send a Firebase Cloud Messaging push notification. Returns True on success."""
    try:
        import firebase_admin
        from firebase_admin import messaging

        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )
        messaging.send(msg)
        return True
    except Exception:
        return False
