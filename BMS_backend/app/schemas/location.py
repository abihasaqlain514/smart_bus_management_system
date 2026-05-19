from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class LocationUpdate(BaseModel):
    """Driver posts this to update bus GPS position."""
    bus_id: UUID
    trip_id: UUID
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)
    speed_kmh: Optional[Decimal] = Field(None, ge=0)
    heading_deg: Optional[Decimal] = Field(None, ge=0, le=360)
    available_seats: Optional[int] = Field(None, ge=0)


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bus_id: UUID
    trip_id: UUID
    latitude: Decimal
    longitude: Decimal
    speed_kmh: Optional[Decimal] = None
    heading_deg: Optional[Decimal] = None
    recorded_at: datetime


class LiveBusOut(BaseModel):
    """Single bus snapshot for the live-tracking dashboard."""
    bus_id: UUID
    bus_number: str
    status: str
    available_seats: int
    capacity: int

    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    speed_kmh: Optional[Decimal] = None
    heading_deg: Optional[Decimal] = None
    recorded_at: Optional[datetime] = None

    driver_name: Optional[str] = None
    driver_code: Optional[str] = None
    route_id: Optional[UUID] = None
    route_name: Optional[str] = None
    route_number: Optional[str] = None

    active_trip_id: Optional[UUID] = None


class NearestStopOut(BaseModel):
    """Returned by GET /locations/nearest — stops sorted by distance from user."""
    stop_id: UUID
    stop_name: str
    stop_order: int
    route_id: UUID
    route_name: str
    route_number: str
    latitude: Decimal
    longitude: Decimal
    distance_km: float
    estimated_minutes: Optional[int] = None
