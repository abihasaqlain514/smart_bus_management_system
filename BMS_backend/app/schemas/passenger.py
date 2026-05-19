from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.passenger import StudentType, Gender


# ── Response schemas ──────────────────────────────────────────────────────────

class PassengerProfileOut(BaseModel):
    """Passenger-specific profile fields (without user base fields)."""
    model_config = ConfigDict(from_attributes=True)

    passenger_id: UUID
    university_id: Optional[str] = None
    department: Optional[str] = None
    student_type: Optional[StudentType] = None
    gender: Optional[Gender] = None
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

    passenger_id: Optional[UUID] = None
    university_id: Optional[str] = None
    department: Optional[str] = None
    student_type: Optional[StudentType] = None
    gender: Optional[Gender] = None
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


# ── Registration / Login ──────────────────────────────────────────────────────

class PassengerRegisterRequest(BaseModel):
    """
    Passenger registration.

    Rules:
    - phone_number must start with country code (+92 for Pakistan)
    - student_type options: bs, bscs, bsse, bsee, bsit, ms, mscs, mphil, phd, faculty, staff
    - university_id must be unique per student

    Seeded accounts (use /login instead for these):
      sara@student.edu.pk    / Sara@1234   / 2021-CS-001
      fatima@student.edu.pk  / Fatima@1234 / 2022-SE-005
      usman@student.edu.pk   / Usman@1234  / 2020-EE-012
    """
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: str = Field(..., min_length=10, max_length=20)
    university_id: str = Field(..., min_length=3, max_length=50)
    student_type: str = Field(..., description="bs / bscs / bsse / bsee / ms / phd / faculty / staff")
    gender: Optional[Gender] = Gender.other

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("Phone number must start with country code, e.g. +92")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Zainab Raza",
                "email": "zainab@student.edu.pk",
                "password": "Zainab@1234",
                "phone_number": "+923451234567",
                "university_id": "2023-CS-100",
                "student_type": "bscs"
            }
        }
    }


class PassengerLoginRequest(BaseModel):
    """
    Passenger login.
    Returns access_token → paste in Authorize (lock icon, top-right).

    Seeded accounts:
      sara@student.edu.pk   / Sara@1234
      fatima@student.edu.pk / Fatima@1234
      usman@student.edu.pk  / Usman@1234
    """
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "sara@student.edu.pk",
                "password": "Sara@1234"
            }
        }
    }
