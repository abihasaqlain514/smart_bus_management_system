import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


class RelationshipType(str, enum.Enum):
    father = "father"
    mother = "mother"
    guardian = "guardian"


class Parent(Base):
    __tablename__ = "parents"

    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user = relationship("User", back_populates="parent_profile")
    children = relationship(
        "ParentChild",
        back_populates="parent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ParentChild(Base):
    """
    Association between a parent and a passenger (child).
    Stores the relationship type and whether the child has verified the link.
    """
    __tablename__ = "parent_children"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parents.parent_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("passengers.passenger_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type = Column(
        SAEnum(RelationshipType, name="relationshiptype"),
        nullable=False,
    )
    is_verified = Column(Boolean, default=False, server_default="false")
    linked_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("Parent", back_populates="children")
    child = relationship("Passenger", back_populates="parent_links", lazy="selectin")
