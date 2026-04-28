from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    permissions = Column(JSONB, default=dict, server_default="{}")
    department = Column(String(100), nullable=True)
    failed_login_count = Column(Integer, default=0, server_default="0")
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="admin_profile")
    audit_logs = relationship("AuditLog", back_populates="admin", lazy="selectin")
    drivers_approved = relationship(
        "Driver",
        foreign_keys="Driver.approved_by",
        back_populates="approver",
        lazy="selectin",
    )
