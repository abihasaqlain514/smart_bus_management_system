from sqlalchemy import Column, ForeignKey, Numeric, DateTime, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class BusLocation(Base):
    __tablename__ = "bus_locations"

    # High-volume GPS table — keep last 24h of records via scheduled cleanup
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bus_id = Column(UUID(as_uuid=True), ForeignKey("buses.id"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    speed_kmh = Column(Numeric(5, 2), nullable=True)
    heading_deg = Column(Numeric(5, 2), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_bus_locations_recorded_at", "recorded_at"),)

    bus = relationship("Bus", back_populates="locations", lazy="selectin")
    trip = relationship("Trip", back_populates="locations", lazy="selectin")
