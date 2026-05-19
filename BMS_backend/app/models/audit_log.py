from sqlalchemy import Column, String, ForeignKey, BigInteger, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id"), nullable=False)
    action = Column(String(100), nullable=False)
    table_name = Column(String(50), nullable=True)
    record_id = Column(String(50), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    admin = relationship("Admin", back_populates="audit_logs")
