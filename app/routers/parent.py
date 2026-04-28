from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_parent
from app.models.user import User, UserRole
from app.models.parent import Parent, ParentChild, RelationshipType
from app.models.passenger import Passenger
from app.models.booking import Booking, BookingStatus
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.models.trip import Trip, TripStatus
from app.models.route import Route, Stop
from app.models.notification import Notification
from app.services.auth_service import hash_password, create_access_token
from app.schemas.parent import (
    ParentRegisterRequest,
    ParentLoginResponse,
    ParentUpdate,
    ParentOut,
    ChildLinkRequest,
    ChildOut,
    ChildTrackingOut,
    ChildBookingStatusOut,
)
from app.schemas.auth import PassengerLoginRequest, UserOut
from app.schemas.notification import NotificationOut
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/api/parent", tags=["Parent"])


# ── Register & Login ──────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_parent(body: ParentRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole.parent,
        phone_number=body.phone_number,
    )
    db.add(user)
    await db.flush()  # get user.id before creating parent row

    parent = Parent(parent_id=user.id)
    db.add(parent)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=ParentLoginResponse)
async def login_parent(body: PassengerLoginRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import verify_password

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.role != UserRole.parent:
        raise HTTPException(status_code=403, detail="Not a parent account")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token(str(user.id), user.role.value)
    return ParentLoginResponse(
        access_token=token,
        token_type="bearer",
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=ParentOut)
async def get_my_profile(
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    parent = await _get_parent_or_404(current_user.id, db)
    return _build_parent_out(current_user, parent)


@router.put("/me", response_model=ParentOut)
async def update_my_profile(
    body: ParentUpdate,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    parent = await _get_parent_or_404(current_user.id, db)

    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone_number is not None:
        current_user.phone_number = body.phone_number
    if body.fcm_token is not None:
        current_user.fcm_token = body.fcm_token
    if body.profile_picture is not None:
        current_user.profile_picture = body.profile_picture

    await db.commit()
    await db.refresh(current_user)
    await db.refresh(parent)
    return _build_parent_out(current_user, parent)


# ── Child Management ──────────────────────────────────────────────────────────

@router.post("/children", response_model=ChildOut, status_code=status.HTTP_201_CREATED)
async def link_child(
    body: ChildLinkRequest,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """Link a child to this parent account by the child's university ID."""
    parent = await _get_parent_or_404(current_user.id, db)

    # Find the passenger by university_id
    result = await db.execute(
        select(Passenger).where(Passenger.university_id == body.university_id)
    )
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="No student found with that university ID")

    # Prevent duplicate links
    existing_link = await db.execute(
        select(ParentChild).where(
            and_(
                ParentChild.parent_id == parent.parent_id,
                ParentChild.child_id == child.passenger_id,
            )
        )
    )
    if existing_link.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Child is already linked to this account")

    link = ParentChild(
        parent_id=parent.parent_id,
        child_id=child.passenger_id,
        relationship_type=body.relationship_type,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return await _build_child_out(link, db)


@router.get("/children", response_model=list[ChildOut])
async def list_children(
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    parent = await _get_parent_or_404(current_user.id, db)
    result = await db.execute(
        select(ParentChild).where(ParentChild.parent_id == parent.parent_id)
    )
    links = result.scalars().all()
    return [await _build_child_out(link, db) for link in links]


@router.delete("/children/{child_id}", response_model=MessageResponse)
async def unlink_child(
    child_id: UUID,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    parent = await _get_parent_or_404(current_user.id, db)
    result = await db.execute(
        select(ParentChild).where(
            and_(
                ParentChild.parent_id == parent.parent_id,
                ParentChild.child_id == child_id,
            )
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Child link not found")

    await db.delete(link)
    await db.commit()
    return MessageResponse(message="Child unlinked successfully")


# ── Live Tracking ─────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/tracking", response_model=ChildTrackingOut)
async def track_child_bus(
    child_id: UUID,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the live GPS position of the bus the child is currently on.
    Looks up:
      1. today's active booking for the child
      2. the active trip on that bus
      3. the latest GPS record from bus_locations
    """
    parent = await _get_parent_or_404(current_user.id, db)
    link = await _get_child_link_or_403(parent.parent_id, child_id, db)

    # Resolve child user info
    child_user_result = await db.execute(select(User).where(User.id == child_id))
    child_user = child_user_result.scalar_one_or_none()

    child_result = await db.execute(
        select(Passenger).where(Passenger.passenger_id == child_id)
    )
    child = child_result.scalar_one_or_none()

    child_name = child_user.full_name if child_user else "Unknown"
    university_id = child.university_id if child else None

    today = date.today()

    # Find today's active or confirmed booking
    booking_result = await db.execute(
        select(Booking).where(
            and_(
                Booking.passenger_id == child_id,
                Booking.booking_date == today,
                Booking.status.in_([BookingStatus.confirmed, BookingStatus.pending]),
            )
        )
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        return ChildTrackingOut(
            child_id=child_id,
            child_name=child_name,
            university_id=university_id,
            has_active_booking=False,
        )

    # Find the active trip on the booked bus
    trip_result = await db.execute(
        select(Trip).where(
            and_(
                Trip.bus_id == booking.bus_id,
                Trip.status == TripStatus.active,
            )
        )
    )
    trip = trip_result.scalar_one_or_none()

    # Get latest GPS location for this bus
    loc_result = await db.execute(
        select(BusLocation)
        .where(BusLocation.bus_id == booking.bus_id)
        .order_by(BusLocation.recorded_at.desc())
        .limit(1)
    )
    location = loc_result.scalar_one_or_none()

    # Get bus details
    bus_result = await db.execute(select(Bus).where(Bus.id == booking.bus_id))
    bus = bus_result.scalar_one_or_none()

    # Get route details
    route_result = await db.execute(select(Route).where(Route.id == booking.route_id))
    route = route_result.scalar_one_or_none()

    # Estimate next stop using last GPS and preferred route stops
    next_stop_name: Optional[str] = None
    estimated_minutes: Optional[int] = None
    if location and route:
        next_stop = await _find_nearest_upcoming_stop(
            float(location.latitude), float(location.longitude), booking.route_id, db
        )
        if next_stop:
            next_stop_name = next_stop.stop_name
            estimated_minutes = next_stop.estimated_minutes

    return ChildTrackingOut(
        child_id=child_id,
        child_name=child_name,
        university_id=university_id,
        has_active_booking=True,
        booking_id=booking.id,
        seat_number=booking.seat_number,
        booking_status=booking.status,
        booking_date=booking.booking_date,
        bus_id=bus.id if bus else None,
        bus_number=bus.bus_number if bus else None,
        bus_status=bus.status if bus else None,
        available_seats=bus.available_seats if bus else None,
        route_id=route.id if route else None,
        route_name=route.route_name if route else None,
        route_number=route.route_number if route else None,
        trip_id=trip.id if trip else None,
        trip_status=trip.status if trip else None,
        trip_started_at=trip.started_at if trip else None,
        latitude=location.latitude if location else None,
        longitude=location.longitude if location else None,
        speed_kmh=location.speed_kmh if location else None,
        heading_deg=location.heading_deg if location else None,
        last_seen_at=location.recorded_at if location else None,
        next_stop_name=next_stop_name,
        estimated_minutes_to_stop=estimated_minutes,
    )


# ── Booking Status ─────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/booking", response_model=ChildBookingStatusOut)
async def get_child_booking_status(
    child_id: UUID,
    booking_date: Optional[date] = None,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """Returns today's (or a given date's) booking status for the child."""
    parent = await _get_parent_or_404(current_user.id, db)
    await _get_child_link_or_403(parent.parent_id, child_id, db)

    check_date = booking_date or date.today()

    child_user_result = await db.execute(select(User).where(User.id == child_id))
    child_user = child_user_result.scalar_one_or_none()

    child_result = await db.execute(
        select(Passenger).where(Passenger.passenger_id == child_id)
    )
    child = child_result.scalar_one_or_none()

    booking_result = await db.execute(
        select(Booking).where(
            and_(
                Booking.passenger_id == child_id,
                Booking.booking_date == check_date,
                Booking.status != BookingStatus.cancelled,
            )
        )
    )
    booking = booking_result.scalar_one_or_none()

    bus: Optional[Bus] = None
    route: Optional[Route] = None
    if booking:
        bus_result = await db.execute(select(Bus).where(Bus.id == booking.bus_id))
        bus = bus_result.scalar_one_or_none()
        route_result = await db.execute(select(Route).where(Route.id == booking.route_id))
        route = route_result.scalar_one_or_none()

    return ChildBookingStatusOut(
        child_id=child_id,
        child_name=child_user.full_name if child_user else "Unknown",
        university_id=child.university_id if child else None,
        booking_date=check_date,
        has_booking=booking is not None,
        booking_id=booking.id if booking else None,
        seat_number=booking.seat_number if booking else None,
        booking_status=booking.status if booking else None,
        bus_id=bus.id if bus else None,
        bus_number=bus.bus_number if bus else None,
        route_id=route.id if route else None,
        route_name=route.route_name if route else None,
        route_number=route.route_number if route else None,
    )


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationOut])
async def get_my_notifications(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.recipient_id == current_user.id,
            )
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_parent_or_404(user_id: UUID, db: AsyncSession) -> Parent:
    result = await db.execute(select(Parent).where(Parent.parent_id == user_id))
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent profile not found")
    return parent


async def _get_child_link_or_403(
    parent_id: UUID, child_id: UUID, db: AsyncSession
) -> ParentChild:
    result = await db.execute(
        select(ParentChild).where(
            and_(
                ParentChild.parent_id == parent_id,
                ParentChild.child_id == child_id,
            )
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=403,
            detail="This child is not linked to your account",
        )
    return link


async def _build_child_out(link: ParentChild, db: AsyncSession) -> ChildOut:
    child_result = await db.execute(
        select(Passenger).where(Passenger.passenger_id == link.child_id)
    )
    child = child_result.scalar_one_or_none()

    user_result = await db.execute(select(User).where(User.id == link.child_id))
    user = user_result.scalar_one_or_none()

    return ChildOut(
        link_id=link.id,
        child_id=link.child_id,
        full_name=user.full_name if user else "Unknown",
        email=user.email if user else "",
        university_id=child.university_id if child else None,
        department=child.department if child else None,
        student_type=child.student_type if child else None,
        relationship_type=link.relationship_type,
        is_verified=link.is_verified,
        linked_at=link.linked_at,
    )


def _build_parent_out(user: User, parent: Parent) -> ParentOut:
    children = []
    for link in (parent.children or []):
        child = link.child       # loaded via selectin
        child_user = child.user if child else None
        children.append(
            ChildOut(
                link_id=link.id,
                child_id=link.child_id,
                full_name=child_user.full_name if child_user else "Unknown",
                email=child_user.email if child_user else "",
                university_id=child.university_id if child else None,
                department=child.department if child else None,
                student_type=child.student_type if child else None,
                relationship_type=link.relationship_type,
                is_verified=link.is_verified,
                linked_at=link.linked_at,
            )
        )
    return ParentOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        profile_picture=user.profile_picture,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        children=children,
    )


async def _find_nearest_upcoming_stop(
    lat: float, lng: float, route_id: UUID, db: AsyncSession
) -> Optional[Stop]:
    """Return the stop on the route closest to the current bus position."""
    import math

    result = await db.execute(
        select(Stop)
        .where(Stop.route_id == route_id)
        .order_by(Stop.stop_order)
    )
    stops = result.scalars().all()
    if not stops:
        return None

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearest = min(
        stops,
        key=lambda s: haversine(lat, lng, float(s.latitude), float(s.longitude)),
    )
    return nearest
