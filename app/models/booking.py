import enum
from sqlalchemy import Column, ForeignKey, Integer, Date, DateTime, Text, Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("passengers.passenger_id"), nullable=False)
    bus_id = Column(UUID(as_uuid=True), ForeignKey("buses.id"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=False)
    seat_number = Column(Integer, nullable=False)
    status = Column(
        SAEnum(BookingStatus, name="bookingstatus"),
        default=BookingStatus.pending,
        server_default="pending",
    )
    booking_date = Column(Date, nullable=False)
    booked_at = Column(DateTime(timezone=True), server_default=func.now())
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # DB-level prevention of duplicate seat bookings
    __table_args__ = (
        UniqueConstraint("bus_id", "seat_number", "booking_date", name="uq_booking_seat"),
    )

    passenger = relationship("Passenger", back_populates="bookings")
    bus = relationship("Bus", back_populates="bookings")
    trip = relationship("Trip", back_populates="bookings")
    route = relationship("Route", back_populates="bookings")
