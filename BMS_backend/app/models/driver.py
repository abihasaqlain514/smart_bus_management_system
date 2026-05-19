import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, Date, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class DriverStatus(str, enum.Enum):
    available  = "available"
    on_trip    = "on_trip"
    offline    = "offline"
    suspended  = "suspended"


class Driver(Base):
    __tablename__ = "drivers"

    driver_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    driver_code  = Column(String(20), unique=True, nullable=False)
    license_number      = Column(String(50), nullable=False)
    license_expiry_date = Column(Date, nullable=True)
    experience_years    = Column(Integer, default=0, server_default="0")

    assigned_bus_id = Column(
        UUID(as_uuid=True),
        ForeignKey("buses.id", use_alter=True, name="fk_drivers_assigned_bus"),
        nullable=True,
    )
    is_online  = Column(Boolean, default=False, server_default="false")
    status     = Column(SAEnum(DriverStatus, name="driverstatus"), default=DriverStatus.offline, server_default="offline")
    avg_rating = Column(Numeric(3, 2), default=0.00, server_default="0.00")
    total_trips = Column(Integer, default=0, server_default="0")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id"), nullable=True)

    user         = relationship("User", back_populates="driver_profile", lazy="selectin")
    assigned_bus = relationship("Bus", foreign_keys=[assigned_bus_id], back_populates="assigned_driver", lazy="selectin")
    trips        = relationship("Trip", back_populates="driver", lazy="selectin")
    issue_reports = relationship("IssueReport", back_populates="driver", lazy="selectin")
    approver     = relationship("Admin", foreign_keys=[approved_by], lazy="selectin")
