import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class NotificationType(str, enum.Enum):
    arriving = "arriving"
    delay = "delay"
    emergency = "emergency"
    cancelled = "cancelled"
    broadcast = "broadcast"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True)
    type = Column(SAEnum(NotificationType, name="notificationtype"), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, server_default="false")
    sent_via_fcm = Column(Boolean, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", back_populates="notifications", lazy="selectin")
    trip = relationship("Trip", back_populates="notifications", lazy="selectin")
