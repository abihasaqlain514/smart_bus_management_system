from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole
from app.models.passenger import StudentType


class PassengerRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    university_id: Optional[str] = Field(None, max_length=30)
    student_type: StudentType
    phone_number: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PassengerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class DriverLoginRequest(BaseModel):
    driver_code: str = Field(..., min_length=3, max_length=20)
    password: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    role: UserRole
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    fcm_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PassengerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"
