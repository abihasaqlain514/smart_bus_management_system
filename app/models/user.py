import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    passenger = "passenger"
    driver = "driver"
    admin = "admin"
    parent = "parent"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="userrole"), nullable=False)
    phone_number = Column(String(20), nullable=True)
    profile_picture = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, server_default="true")
    is_verified = Column(Boolean, default=False, server_default="false")
    fcm_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    passenger_profile = relationship("Passenger", back_populates="user", uselist=False, lazy="selectin")
    driver_profile = relationship("Driver", back_populates="user", uselist=False, lazy="selectin")
    admin_profile = relationship("Admin", back_populates="user", uselist=False, lazy="selectin")
    parent_profile = relationship("Parent", back_populates="user", uselist=False, lazy="selectin")
    notifications = relationship("Notification", back_populates="recipient", lazy="selectin")
