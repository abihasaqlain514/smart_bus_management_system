from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.models.driver import DriverStatus
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import Optional
 


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
    assigned_bus_id: Optional[UUID] = None
    status: Optional[DriverStatus] = None


class DriverProfileOut(BaseModel):
    """Driver-specific fields only."""
    model_config = ConfigDict(from_attributes=True)

    driver_id: UUID
    driver_code: str
    license_number: str
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
    assigned_bus_id: Optional[UUID] = None
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

class DriverRegisterRequest(BaseModel):
    """Schema for driver registration"""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the driver")
    email: EmailStr = Field(..., description="Driver's email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Driver's phone number")
    driver_code: str = Field(..., min_length=4, max_length=20, description="Unique driver code/ID")
    license_number: str = Field(..., min_length=5, max_length=50, description="Driver's license number")
    license_expiry_date: date = Field(..., description="License expiry date (YYYY-MM-DD)")
    experience_years: int = Field(..., ge=0, le=50, description="Years of driving experience")
 
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith('+'):
            raise ValueError('Phone number must start with country code (e.g., +92)')
        return v
    
    @field_validator('driver_code')
    @classmethod
    def validate_driver_code(cls, v: str) -> str:
        # Remove whitespace
        v = v.strip().upper()
        if not v:
            raise ValueError('Driver code cannot be empty')
        return v
    
    @field_validator('license_expiry_date')
    @classmethod
    def validate_license_expiry(cls, v: date) -> date:
        from datetime import date as date_type
        if v < date_type.today():
            raise ValueError('License expiry date must be in the future')
        return v
 
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ahmed Ali",
                "email": "ahmed.driver@example.com",
                "password": "SecurePass123!",
                "phone_number": "+923001234567",
                "driver_code": "DRV001",
                "license_number": "LHR-123456-2025",
                "license_expiry_date": "2028-12-31",
                "experience_years": 5
            }
        }
 
 
class DriverLoginRequest(BaseModel):
    """Schema for driver login"""
    driver_code: str = Field(..., description="Unique driver code")
    password: str = Field(..., description="Driver's password")
 
    class Config:
        json_schema_extra = {
            "example": {
                "driver_code": "DRV001",
                "password": "SecurePass123!"
            }
        }