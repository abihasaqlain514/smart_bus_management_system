import enum
from sqlalchemy import Column, ForeignKey, Integer, Numeric, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class TripStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.driver_id"), nullable=False)
    bus_id = Column(UUID(as_uuid=True), ForeignKey("buses.id"), nullable=False)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=False)
    status = Column(
        SAEnum(TripStatus, name="tripstatus"),
        default=TripStatus.active,
        server_default="active",
    )
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    total_distance_km = Column(Numeric(8, 2), nullable=True)
    total_passengers = Column(Integer, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    driver = relationship("Driver", back_populates="trips", lazy="selectin")
    bus = relationship("Bus", back_populates="trips", lazy="selectin")
    route = relationship("Route", back_populates="trips", lazy="selectin")
    locations = relationship("BusLocation", back_populates="trip", lazy="selectin")
    bookings = relationship("Booking", back_populates="trip", lazy="selectin")
    notifications = relationship("Notification", back_populates="trip", lazy="selectin")
    issue_reports = relationship("IssueReport", back_populates="trip", lazy="selectin")
