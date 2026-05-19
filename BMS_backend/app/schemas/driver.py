from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from app.models.driver import DriverStatus


# ── Response schemas ──────────────────────────────────────────────────────────

class DriverCreate(BaseModel):
    """Admin creates a driver account — driver does not self-register."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)
    driver_code: str = Field(..., min_length=3, max_length=20)
    license_number: str = Field(..., min_length=5, max_length=50)


class DriverUpdate(BaseModel):
    """Admin updates a driver record."""
    license_number: Optional[str] = Field(None, max_length=50)
    license_expiry_date: Optional[date] = None
    experience_years: Optional[int] = Field(None, ge=0)
    assigned_bus_id: Optional[UUID] = None
    status: Optional[DriverStatus] = None


class DriverProfileOut(BaseModel):
    """Driver-specific fields only."""
    model_config = ConfigDict(from_attributes=True)

    driver_id: UUID
    driver_code: str
    license_number: str
    license_expiry_date: Optional[date] = None
    experience_years: int = 0
    assigned_bus_id: Optional[UUID] = None
    is_online: bool
    status: DriverStatus
    avg_rating: Optional[Decimal] = None
    total_trips: int
    approved_by: Optional[UUID] = None


class DriverOut(BaseModel):
    """Full driver view — user fields + driver profile."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    is_active: bool
    created_at: datetime

    driver_id: Optional[UUID] = None
    driver_code: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry_date: Optional[date] = None
    experience_years: int = 0
    assigned_bus_id: Optional[UUID] = None
    bus_number: Optional[str] = None
    bus_route_id: Optional[UUID] = None
    route_name: Optional[str] = None
    is_online: bool = False
    status: Optional[DriverStatus] = None
    avg_rating: Optional[Decimal] = None
    total_trips: int = 0


class DriverWithBusRoute(DriverOut):
    """Extended response for driver login — includes bus and route info."""
    bus_number: Optional[str] = None
    bus_plate_number: Optional[str] = None
    route_name: Optional[str] = None
    route_number: Optional[str] = None


class DriverLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    driver: DriverWithBusRoute


class DriverListItem(BaseModel):
    """Compact row for admin lists."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    driver_code: Optional[str] = None
    status: Optional[DriverStatus] = None
    is_online: bool = False
    total_trips: int = 0
    avg_rating: Optional[Decimal] = None
    is_active: bool
    created_at: datetime


# ── Registration / Login ──────────────────────────────────────────────────────

class DriverRegisterRequest(BaseModel):
    """
    Driver self-registration.

    Rules:
    - driver_code is auto-uppercased (drv-003 → DRV-003)
    - phone_number must start with country code (+92)
    - license_expiry_date must be a future date (YYYY-MM-DD)
    - password: min 8 chars

    Existing seeded drivers: DRV-001 (Ahmed Khan), DRV-002 (Bilal Hussain).
    Use a new driver_code to avoid 409 conflict.
    """
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone_number: str = Field(..., min_length=10, max_length=20)
    driver_code: str = Field(..., min_length=4, max_length=20)
    license_number: str = Field(..., min_length=5, max_length=50)
    license_expiry_date: date = Field(..., description="License expiry date (YYYY-MM-DD)")
    experience_years: int = Field(0, ge=0, le=50)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("Phone number must start with country code, e.g. +92")
        return v

    @field_validator("driver_code")
    @classmethod
    def normalize_driver_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("license_expiry_date")
    @classmethod
    def validate_expiry(cls, v: date) -> date:
        from datetime import date as today_type
        if v < today_type.today():
            raise ValueError("License expiry date must be in the future")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Hassan Raza",
                "email": "hassan.driver@smartbus.com",
                "password": "Driver@1234",
                "phone_number": "+923009876543",
                "driver_code": "DRV-003",
                "license_number": "LHR-DL-2024-003",
                "license_expiry_date": "2029-06-30",
                "experience_years": 3
            }
        }
    }


class DriverLoginRequest(BaseModel):
    """
    Driver login using driver_code + password.
    Returns access_token → paste in Authorize (lock icon, top-right).

    Seeded accounts:
      DRV-001 / Driver@1234  (Ahmed Khan)
      DRV-002 / Driver@1234  (Bilal Hussain)
    """
    driver_code: str = Field(..., description="Unique driver code, e.g. DRV-001")
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "driver_code": "DRV-001",
                "password": "Driver@1234"
            }
        }
    }
