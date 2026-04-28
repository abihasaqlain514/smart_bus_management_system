"""init_tables

Revision ID: 001
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Enum types
    userrole = postgresql.ENUM("passenger", "driver", "admin", name="userrole", create_type=False)
    studenttype = postgresql.ENUM("bs", "ms", "phd", "faculty", "staff", name="studenttype", create_type=False)
    driverstatus = postgresql.ENUM("available", "on_trip", "offline", "suspended", name="driverstatus", create_type=False)
    busstatus = postgresql.ENUM("on_route", "delayed", "not_in_service", "breakdown", name="busstatus", create_type=False)
    tripstatus = postgresql.ENUM("active", "completed", "cancelled", name="tripstatus", create_type=False)
    bookingstatus = postgresql.ENUM("pending", "confirmed", "cancelled", "completed", name="bookingstatus", create_type=False)
    notificationtype = postgresql.ENUM("arriving", "delay", "emergency", "cancelled", "broadcast", name="notificationtype", create_type=False)
    issuetype = postgresql.ENUM("breakdown", "delay", "accident", "emergency", name="issuetype", create_type=False)
    issueseverity = postgresql.ENUM("low", "medium", "high", "critical", name="issueseverity", create_type=False)
    issuestatus = postgresql.ENUM("open", "acknowledged", "resolved", name="issuestatus", create_type=False)

    for e in [userrole, studenttype, driverstatus, busstatus, tripstatus, bookingstatus, notificationtype, issuetype, issueseverity, issuestatus]:
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("passenger", "driver", "admin", name="userrole"), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("profile_picture", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("fcm_token", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "admins",
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permissions", postgresql.JSONB, server_default="{}"),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("failed_login_count", sa.Integer, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("route_name", sa.String(100), nullable=False),
        sa.Column("route_number", sa.String(20), nullable=False, unique=True),
        sa.Column("start_point", sa.String(150), nullable=False),
        sa.Column("end_point", sa.String(150), nullable=False),
        sa.Column("distance_km", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stop_name", sa.String(150), nullable=False),
        sa.Column("stop_order", sa.Integer, nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("estimated_minutes", sa.Integer, nullable=True),
    )

    op.create_table(
        "buses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("bus_number", sa.String(20), nullable=False, unique=True),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column("available_seats", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("on_route", "delayed", "not_in_service", "breakdown", name="busstatus"), server_default="not_in_service"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("plate_number", sa.String(20), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "drivers",
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("driver_code", sa.String(20), nullable=False, unique=True),
        sa.Column("license_number", sa.String(50), nullable=False),
        sa.Column("assigned_bus_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_online", sa.Boolean, server_default="false"),
        sa.Column("status", sa.Enum("available", "on_trip", "offline", "suspended", name="driverstatus"), server_default="offline"),
        sa.Column("avg_rating", sa.Numeric(3, 2), server_default="0.00"),
        sa.Column("total_trips", sa.Integer, server_default="0"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.admin_id"), nullable=True),
    )

    op.create_table(
        "passengers",
        sa.Column("passenger_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("university_id", sa.String(30), unique=True, nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("student_type", sa.Enum("bs", "ms", "phd", "faculty", "staff", name="studenttype"), nullable=False),
        sa.Column("is_hostel_resident", sa.Boolean, server_default="false"),
        sa.Column("preferred_route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=True),
    )

    # Add deferred FKs for buses ↔ drivers circular reference
    op.create_foreign_key("fk_buses_driver_id", "buses", "drivers", ["driver_id"], ["driver_id"], use_alter=True)
    op.create_foreign_key("fk_drivers_assigned_bus", "drivers", "buses", ["assigned_bus_id"], ["id"], use_alter=True)

    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.driver_id"), nullable=False),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("status", sa.Enum("active", "completed", "cancelled", name="tripstatus"), server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_distance_km", sa.Numeric(8, 2), nullable=True),
        sa.Column("total_passengers", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "bus_locations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("speed_kmh", sa.Numeric(5, 2), nullable=True),
        sa.Column("heading_deg", sa.Numeric(5, 2), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bus_locations_recorded_at", "bus_locations", ["recorded_at"])

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("passenger_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("passengers.passenger_id"), nullable=False),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("seat_number", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("pending", "confirmed", "cancelled", "completed", name="bookingstatus"), server_default="pending"),
        sa.Column("booking_date", sa.Date, nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.UniqueConstraint("bus_id", "seat_number", "booking_date", name="uq_booking_seat"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column("type", sa.Enum("arriving", "delay", "emergency", "cancelled", "broadcast", name="notificationtype"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("sent_via_fcm", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "issue_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.driver_id"), nullable=False),
        sa.Column("issue_type", sa.Enum("breakdown", "delay", "accident", "emergency", name="issuetype"), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.Enum("low", "medium", "high", "critical", name="issueseverity"), nullable=False),
        sa.Column("status", sa.Enum("open", "acknowledged", "resolved", name="issuestatus"), server_default="open"),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.admin_id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("table_name", sa.String(50), nullable=True),
        sa.Column("record_id", sa.String(50), nullable=True),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("issue_reports")
    op.drop_table("notifications")
    op.drop_table("bookings")
    op.drop_table("bus_locations")
    op.drop_table("trips")
    op.drop_constraint("fk_buses_driver_id", "buses", type_="foreignkey")
    op.drop_constraint("fk_drivers_assigned_bus", "drivers", type_="foreignkey")
    op.drop_table("passengers")
    op.drop_table("drivers")
    op.drop_table("buses")
    op.drop_table("stops")
    op.drop_table("routes")
    op.drop_table("admins")
    op.drop_table("users")

    for name in ["userrole", "studenttype", "driverstatus", "busstatus", "tripstatus",
                 "bookingstatus", "notificationtype", "issuetype", "issueseverity", "issuestatus"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
