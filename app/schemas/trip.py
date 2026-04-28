from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.models.trip import TripStatus


class TripStart(BaseModel):
    bus_id: UUID
    route_id: UUID


class TripStatusUpdate(BaseModel):
    status: TripStatus


class TripSeatUpdate(BaseModel):
    available_seats: int = Field(..., ge=0)


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    driver_id: UUID
    bus_id: UUID
    route_id: UUID
    status: TripStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_distance_km: Optional[Decimal] = None
    total_passengers: int
    created_at: datetime


class TripWithDetails(BaseModel):
    """Extended trip view with resolved names — used in list and active-trip endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: TripStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_distance_km: Optional[Decimal] = None
    total_passengers: int
    created_at: datetime

    driver_id: UUID
    driver_name: Optional[str] = None
    driver_code: Optional[str] = None

    bus_id: UUID
    bus_number: Optional[str] = None

    route_id: UUID
    route_name: Optional[str] = None
    route_number: Optional[str] = None


class ETAResponse(BaseModel):
    """Response for GET /trips/{trip_id}/eta."""
    trip_id: UUID
    bus_id: UUID
    next_stop_id: Optional[UUID] = None
    next_stop_name: Optional[str] = None
    distance_to_stop_km: Optional[float] = None
    estimated_minutes: Optional[int] = None
    current_speed_kmh: Optional[float] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None


class StopArrivalOut(BaseModel):
    """Returned when a driver marks arrival at a stop."""
    trip_id: UUID
    stop_id: UUID
    stop_name: str
    arrived_at: datetime
