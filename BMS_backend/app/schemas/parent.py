from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from app.models.parent import RelationshipType
from app.models.passenger import StudentType
from app.models.booking import BookingStatus
from app.models.bus import BusStatus
from app.models.trip import TripStatus


# ── Registration ──────────────────────────────────────────────────────────────

class ParentRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)


class ParentLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: UUID
    full_name: str
    email: str
    role: str


# ── Profile ───────────────────────────────────────────────────────────────────

class ParentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    fcm_token: Optional[str] = None
    profile_picture: Optional[str] = None


# ── Child management ──────────────────────────────────────────────────────────

class ChildLinkRequest(BaseModel):
    """Parent links a child by their university ID."""
    university_id: str = Field(..., min_length=3, max_length=30)
    relationship_type: RelationshipType


class ChildOut(BaseModel):
    """A child as seen by a parent."""
    model_config = ConfigDict(from_attributes=True)

    link_id: UUID                           # ParentChild.id
    child_id: UUID                          # passenger_id
    full_name: str
    email: str
    university_id: Optional[str] = None
    department: Optional[str] = None
    student_type: Optional[StudentType] = None
    relationship_type: RelationshipType
    is_verified: bool
    linked_at: datetime


class ParentOut(BaseModel):
    """Full parent profile returned by GET /parent/me."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    children: List[ChildOut] = []


# ── Live tracking ─────────────────────────────────────────────────────────────

class ChildTrackingOut(BaseModel):
    """
    Live bus tracking snapshot for a linked child.
    Returned by GET /parent/children/{child_id}/tracking
    """
    child_id: UUID
    child_name: str
    university_id: Optional[str] = None

    # Booking state
    has_active_booking: bool
    booking_id: Optional[UUID] = None
    seat_number: Optional[int] = None
    booking_status: Optional[BookingStatus] = None
    booking_date: Optional[date] = None

    # Bus info
    bus_id: Optional[UUID] = None
    bus_number: Optional[str] = None
    bus_status: Optional[BusStatus] = None
    available_seats: Optional[int] = None

    # Route
    route_id: Optional[UUID] = None
    route_name: Optional[str] = None
    route_number: Optional[str] = None

    # Active trip
    trip_id: Optional[UUID] = None
    trip_status: Optional[TripStatus] = None
    trip_started_at: Optional[datetime] = None

    # GPS (latest record for the bus)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    speed_kmh: Optional[Decimal] = None
    heading_deg: Optional[Decimal] = None
    last_seen_at: Optional[datetime] = None

    # ETA to child's stop (estimated)
    next_stop_name: Optional[str] = None
    estimated_minutes_to_stop: Optional[int] = None


# ── Child booking status ───────────────────────────────────────────────────────

class ChildBookingStatusOut(BaseModel):
    """
    Today's booking status for a linked child.
    Returned by GET /parent/children/{child_id}/booking
    """
    child_id: UUID
    child_name: str
    university_id: Optional[str] = None
    booking_date: date

    has_booking: bool
    booking_id: Optional[UUID] = None
    seat_number: Optional[int] = None
    booking_status: Optional[BookingStatus] = None

    bus_id: Optional[UUID] = None
    bus_number: Optional[str] = None
    route_id: Optional[UUID] = None
    route_name: Optional[str] = None
    route_number: Optional[str] = None
