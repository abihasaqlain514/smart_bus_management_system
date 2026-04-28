from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    bus_id: UUID
    route_id: UUID
    seat_number: int = Field(..., ge=1)
    booking_date: date


class BookingCancel(BaseModel):
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    passenger_id: UUID
    bus_id: UUID
    trip_id: Optional[UUID] = None
    route_id: UUID
    seat_number: int
    status: BookingStatus
    booking_date: date
    booked_at: datetime
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None


class BookingWithDetails(BaseModel):
    """Extended booking view — names resolved for display."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seat_number: int
    status: BookingStatus
    booking_date: date
    booked_at: datetime
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    passenger_id: UUID
    passenger_name: Optional[str] = None
    university_id: Optional[str] = None

    bus_id: UUID
    bus_number: Optional[str] = None

    route_id: UUID
    route_name: Optional[str] = None
    route_number: Optional[str] = None

    trip_id: Optional[UUID] = None


class BookingStatusUpdate(BaseModel):
    """Admin or driver can confirm or complete a booking."""
    status: BookingStatus
