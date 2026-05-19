import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class BusStatus(str, enum.Enum):
    on_route = "on_route"
    delayed = "delayed"
    not_in_service = "not_in_service"
    breakdown = "breakdown"


class Bus(Base):
    __tablename__ = "buses"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bus_number = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    status = Column(
        SAEnum(BusStatus, name="busstatus"),
        default=BusStatus.not_in_service,
        server_default="not_in_service",
    )
    is_active = Column(Boolean, default=True, server_default="true")
    # use_alter breaks the circular FK with drivers
    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id", use_alter=True, name="fk_buses_driver_id"),
        nullable=True,
    )
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)
    model = Column(String(100), nullable=True)
    plate_number = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    current_driver = relationship(
        "Driver",
        foreign_keys=[driver_id],
        lazy="selectin",
        primaryjoin="Bus.driver_id == Driver.driver_id",
    )
    assigned_driver = relationship(
        "Driver",
        foreign_keys="[Driver.assigned_bus_id]",
        back_populates="assigned_bus",
        lazy="selectin",
    )
    route = relationship("Route", back_populates="buses", lazy="selectin")
    trips = relationship("Trip", back_populates="bus", lazy="selectin")
    locations = relationship("BusLocation", back_populates="bus", lazy="selectin")
    bookings = relationship("Booking", back_populates="bus", lazy="selectin")
