from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class BusAssignRequest(BaseModel):
    """Human-readable bus assignment — no UUIDs required."""
    bus_number:   str = Field(..., description="Bus number e.g. JHG-001")
    driver_code:  Optional[str] = Field(None, description="Driver code e.g. DRV-JHG-01")
    route_number: Optional[str] = Field(None, description="Route number e.g. R-JHG-01")
    bus_status:   Optional[str] = Field(None, description="on_route / not_in_service / delayed")


# ── Response schemas ──────────────────────────────────────────────────────────

class AdminCreate(BaseModel):
    """Super-admin creates another admin account."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    permissions: Optional[dict] = None


class AdminUpdate(BaseModel):
    department: Optional[str] = Field(None, max_length=100)
    permissions: Optional[dict] = None


class AdminProfileOut(BaseModel):
    """Admin-specific fields only."""
    model_config = ConfigDict(from_attributes=True)

    admin_id: UUID
    department: Optional[str] = None
    permissions: Optional[Any] = None
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AdminOut(BaseModel):
    """Full admin view — user fields + admin profile."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    admin_id: Optional[UUID] = None
    department: Optional[str] = None
    permissions: Optional[Any] = None
    last_login_at: Optional[datetime] = None


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminOut


class AdminListItem(BaseModel):
    """Compact row for admin management lists."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    department: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


# ── Registration / Login ──────────────────────────────────────────────────────

class AdminRegisterRequest(BaseModel):
    """
    Admin registration.

    Rules:
    - password: min 8 chars, must have uppercase + lowercase + digit
    - phone_number: must start with country code (+92 for Pakistan)
    - department: optional

    If email already exists you get 409 — use /api/auth/admin/login instead.
    """
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone_number: str = Field(..., min_length=10, max_length=20)
    department: Optional[str] = Field(None, max_length=100)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("Phone number must start with country code, e.g. +92")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must have at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must have at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must have at least one digit")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "System Admin",
                "email": "admin@smartbus.com",
                "password": "Admin@1234",
                "phone_number": "+923001111111",
                "department": "Transport Management"
            }
        }
    }


class AdminLoginRequest(BaseModel):
    """
    Admin login.
    After 3 wrong passwords the account is locked for 15 minutes.
    Returns access_token → paste in Authorize (lock icon, top-right).
    """
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@smartbus.com",
                "password": "Admin@1234"
            }
        }
    }
