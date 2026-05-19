from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole


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


class PassengerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"
