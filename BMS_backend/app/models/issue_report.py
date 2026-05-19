import enum
from sqlalchemy import Column, ForeignKey, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class IssueType(str, enum.Enum):
    breakdown = "breakdown"
    delay = "delay"
    accident = "accident"
    emergency = "emergency"


class IssueSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IssueStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class IssueReport(Base):
    __tablename__ = "issue_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.driver_id"), nullable=False)
    issue_type = Column(SAEnum(IssueType, name="issuetype"), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SAEnum(IssueSeverity, name="issueseverity"), nullable=False)
    status = Column(
        SAEnum(IssueStatus, name="issuestatus"),
        default=IssueStatus.open,
        server_default="open",
    )
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    trip = relationship("Trip", back_populates="issue_reports", lazy="selectin")
    driver = relationship("Driver", back_populates="issue_reports", lazy="selectin")
