from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.issue_report import IssueType, IssueSeverity, IssueStatus


class IssueReportCreate(BaseModel):
    """Driver files an issue report during a trip."""
    trip_id: UUID
    issue_type: IssueType
    description: Optional[str] = Field(None, max_length=2000)
    severity: IssueSeverity


class IssueReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    driver_id: UUID
    issue_type: IssueType
    description: Optional[str] = None
    severity: IssueSeverity
    status: IssueStatus
    reported_at: datetime
    resolved_at: Optional[datetime] = None


class IssueReportWithDetails(BaseModel):
    """Extended view for admin — includes driver name and bus number."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_type: IssueType
    description: Optional[str] = None
    severity: IssueSeverity
    status: IssueStatus
    reported_at: datetime
    resolved_at: Optional[datetime] = None

    trip_id: UUID
    driver_id: UUID
    driver_name: Optional[str] = None
    driver_code: Optional[str] = None
    bus_number: Optional[str] = None
    route_name: Optional[str] = None


class IssueStatusUpdate(BaseModel):
    """Admin acknowledges or resolves an issue."""
    status: IssueStatus
