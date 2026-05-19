import enum
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class StudentType(str, enum.Enum):
    # Undergraduate
    bs     = "bs"
    bscs   = "bscs"
    bsse   = "bsse"
    bsee   = "bsee"
    bsit   = "bsit"
    bsme   = "bsme"
    bba    = "bba"
    # Postgraduate
    ms     = "ms"
    mscs   = "mscs"
    msse   = "msse"
    mba    = "mba"
    mphil  = "mphil"
    phd    = "phd"
    # Non-student roles at university
    faculty = "faculty"
    staff   = "staff"


class Gender(str, enum.Enum):
    male   = "male"
    female = "female"
    other  = "other"


class Passenger(Base):
    __tablename__ = "passengers"

    passenger_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    university_id = Column(String(30), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    student_type = Column(String(30), nullable=False)
    gender = Column(String(10), nullable=True, default="other")
    is_hostel_resident = Column(Boolean, default=False, server_default="false")
    preferred_route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)

    user = relationship("User", back_populates="passenger_profile", lazy="selectin")
    preferred_route = relationship("Route", back_populates="preferred_passengers", lazy="selectin")
    bookings = relationship("Booking", back_populates="passenger", lazy="selectin")
    parent_links = relationship("ParentChild", back_populates="child", lazy="selectin")
