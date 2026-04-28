from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class StopCreate(BaseModel):
    stop_name: str = Field(..., min_length=2, max_length=150)
    stop_order: int = Field(..., ge=1)
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)
    estimated_minutes: Optional[int] = Field(None, ge=0)


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    route_id: UUID
    stop_name: str
    stop_order: int
    latitude: Decimal
    longitude: Decimal
    estimated_minutes: Optional[int] = None


class StopUpdate(BaseModel):
    stop_name: Optional[str] = Field(None, max_length=150)
    stop_order: Optional[int] = Field(None, ge=1)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    estimated_minutes: Optional[int] = Field(None, ge=0)


class RouteCreate(BaseModel):
    route_name: str = Field(..., min_length=2, max_length=100)
    route_number: str = Field(..., min_length=1, max_length=20)
    start_point: str = Field(..., min_length=2, max_length=150)
    end_point: str = Field(..., min_length=2, max_length=150)
    distance_km: Optional[Decimal] = Field(None, ge=0)


class RouteUpdate(BaseModel):
    route_name: Optional[str] = Field(None, max_length=100)
    start_point: Optional[str] = Field(None, max_length=150)
    end_point: Optional[str] = Field(None, max_length=150)
    distance_km: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    route_name: str
    route_number: str
    start_point: str
    end_point: str
    distance_km: Optional[Decimal] = None
    is_active: bool
    created_at: datetime
    stops: List[StopOut] = []


class RouteListItem(BaseModel):
    """Compact route row without stops for list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    route_name: str
    route_number: str
    start_point: str
    end_point: str
    distance_km: Optional[Decimal] = None
    is_active: bool
    stop_count: int = 0
