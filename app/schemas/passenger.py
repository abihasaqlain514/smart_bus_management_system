from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.passenger import StudentType
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import Optional


class PassengerProfileOut(BaseModel):
    """Passenger-specific profile fields (without user base fields)."""
    model_config = ConfigDict(from_attributes=True)

    passenger_id: UUID
    university_id: Optional[str] = None
    department: Optional[str] = None
    student_type: StudentType
    is_hostel_resident: bool
    preferred_route_id: Optional[UUID] = None


class PassengerOut(BaseModel):
    """Full passenger view — user fields + passenger profile fields."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    # nested passenger profile
    passenger_id: Optional[UUID] = None
    university_id: Optional[str] = None
    department: Optional[str] = None
    student_type: Optional[StudentType] = None
    is_hostel_resident: bool = False
    preferred_route_id: Optional[UUID] = None


class PassengerUpdate(BaseModel):
    """Fields a passenger can update about themselves."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    is_hostel_resident: Optional[bool] = None
    preferred_route_id: Optional[UUID] = None
    fcm_token: Optional[str] = None
    profile_picture: Optional[str] = None


class PassengerListItem(BaseModel):
    """Compact row used in admin paginated lists."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    university_id: Optional[str] = None
    student_type: Optional[StudentType] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime


class PassengerRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: str = Field(..., min_length=10, max_length=20)
    university_id: str = Field(..., min_length=3, max_length=50)
    student_type: str = Field(..., description="e.g., undergraduate, graduate")
 
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Basic phone validation - customize as needed
        if not v.startswith('+'):
            raise ValueError('Phone number must start with country code (e.g., +1)')
        return v
 
 
class PassengerLoginRequest(BaseModel):
    email: EmailStr
    password: str