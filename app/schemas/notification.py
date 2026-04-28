from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.notification import NotificationType
from app.models.user import UserRole


class NotificationSend(BaseModel):
    """Driver sends a notification to passengers on a route."""
    type: NotificationType
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1)
    trip_id: Optional[UUID] = None


class BroadcastNotification(BaseModel):
    """Admin broadcasts to all users or a specific role."""
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1)
    target_role: Optional[UserRole] = None   # None → send to every user


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_id: UUID
    trip_id: Optional[UUID] = None
    type: NotificationType
    title: str
    message: str
    is_read: bool
    sent_via_fcm: bool
    created_at: datetime


class NotificationMarkRead(BaseModel):
    is_read: bool = True
