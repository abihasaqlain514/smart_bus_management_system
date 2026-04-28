from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import Optional
 


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

class AdminRegisterRequest(BaseModel):
    """Schema for admin registration"""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the admin")
    email: EmailStr = Field(..., description="Admin's email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Admin's phone number")
    department: Optional[str] = Field(None, max_length=100, description="Department (optional)")
 
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith('+'):
            raise ValueError('Phone number must start with country code (e.g., +92)')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce strong password for admin accounts"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, and one digit'
            )
        return v
 
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Muhammad Hassan",
                "email": "admin@university.edu.pk",
                "password": "AdminPass123!",
                "phone_number": "+923001234567",
                "department": "Transport Management"
            }
        }
 
class AdminLoginRequest(BaseModel):
    """Schema for admin login"""
    email: EmailStr = Field(..., description="Admin's email address")
    password: str = Field(..., description="Admin's password")
 
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@university.edu.pk",
                "password": "AdminPass123!"
            }
        }
