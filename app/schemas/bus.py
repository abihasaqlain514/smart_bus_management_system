from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.bus import BusStatus


class BusCreate(BaseModel):
    bus_number: str = Field(..., min_length=1, max_length=20)
    capacity: int = Field(..., gt=0, le=200)
    model: Optional[str] = Field(None, max_length=100)
    plate_number: Optional[str] = Field(None, max_length=20)
    route_id: Optional[UUID] = None

    @field_validator("capacity")
    @classmethod
    def capacity_valid(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Capacity must be at least 1")
        return v


class BusUpdate(BaseModel):
    bus_number: Optional[str] = Field(None, max_length=20)
    capacity: Optional[int] = Field(None, gt=0)
    available_seats: Optional[int] = Field(None, ge=0)
    status: Optional[BusStatus] = None
    driver_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    model: Optional[str] = Field(None, max_length=100)
    plate_number: Optional[str] = Field(None, max_length=20)


class BusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bus_number: str
    capacity: int
    available_seats: int
    status: BusStatus
    is_active: bool
    driver_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    model: Optional[str] = None
    plate_number: Optional[str] = None
    created_at: datetime


class BusWithDetails(BaseModel):
    """Extended bus view for monitoring dashboard — includes resolved names."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bus_number: str
    capacity: int
    available_seats: int
    status: BusStatus
    is_active: bool
    model: Optional[str] = None
    plate_number: Optional[str] = None
    created_at: datetime

    driver_id: Optional[UUID] = None
    driver_name: Optional[str] = None
    driver_code: Optional[str] = None
    route_id: Optional[UUID] = None
    route_name: Optional[str] = None
    route_number: Optional[str] = None

    # Latest GPS snapshot (populated by the monitoring endpoint)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_seen_at: Optional[datetime] = None
