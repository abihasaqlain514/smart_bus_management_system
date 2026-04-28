from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    route_name = Column(String(100), nullable=False)
    route_number = Column(String(20), unique=True, nullable=False, index=True)
    start_point = Column(String(150), nullable=False)
    end_point = Column(String(150), nullable=False)
    distance_km = Column(Numeric(6, 2), nullable=True)
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stops = relationship(
        "Stop",
        back_populates="route",
        order_by="Stop.stop_order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    buses = relationship("Bus", back_populates="route", lazy="selectin")
    trips = relationship("Trip", back_populates="route", lazy="selectin")
    bookings = relationship("Booking", back_populates="route", lazy="selectin")
    preferred_passengers = relationship("Passenger", back_populates="preferred_route", lazy="selectin")


class Stop(Base):
    __tablename__ = "stops"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    stop_name = Column(String(150), nullable=False)
    stop_order = Column(Integer, nullable=False)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    estimated_minutes = Column(Integer, nullable=True)

    route = relationship("Route", back_populates="stops")
