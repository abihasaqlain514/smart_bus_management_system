from app.schemas.common import PaginatedResponse, MessageResponse, SuccessResponse

from app.schemas.auth import (
    PassengerRegisterRequest,
    PassengerLoginRequest,
    DriverLoginRequest,
    AdminLoginRequest,
    TokenResponse,
    UserOut,
    PassengerLoginResponse,
    LogoutResponse,
)

from app.schemas.passenger import (
    PassengerProfileOut,
    PassengerOut,
    PassengerUpdate,
    PassengerListItem,
)

from app.schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverProfileOut,
    DriverOut,
    DriverWithBusRoute,
    DriverLoginResponse,
    DriverListItem,
)

from app.schemas.admin import (
    AdminCreate,
    AdminUpdate,
    AdminProfileOut,
    AdminOut,
    AdminLoginResponse,
    AdminListItem,
)

from app.schemas.bus import (
    BusCreate,
    BusUpdate,
    BusOut,
    BusWithDetails,
)

from app.schemas.route import (
    StopCreate,
    StopOut,
    StopUpdate,
    RouteCreate,
    RouteUpdate,
    RouteOut,
    RouteListItem,
)

from app.schemas.trip import (
    TripStart,
    TripStatusUpdate,
    TripSeatUpdate,
    TripOut,
    TripWithDetails,
    ETAResponse,
    StopArrivalOut,
)

from app.schemas.booking import (
    BookingCreate,
    BookingCancel,
    BookingOut,
    BookingWithDetails,
    BookingStatusUpdate,
)

from app.schemas.location import (
    LocationUpdate,
    LocationOut,
    LiveBusOut,
    NearestStopOut,
)

from app.schemas.notification import (
    NotificationSend,
    BroadcastNotification,
    NotificationOut,
    NotificationMarkRead,
)

from app.schemas.issue_report import (
    IssueReportCreate,
    IssueReportOut,
    IssueReportWithDetails,
    IssueStatusUpdate,
)

from app.schemas.audit_log import AuditLogOut

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

__all__ = [
    # common
    "PaginatedResponse", "MessageResponse", "SuccessResponse",
    # auth
    "PassengerRegisterRequest", "PassengerLoginRequest", "DriverLoginRequest",
    "AdminLoginRequest", "TokenResponse", "UserOut", "PassengerLoginResponse", "LogoutResponse",
    # passenger
    "PassengerProfileOut", "PassengerOut", "PassengerUpdate", "PassengerListItem",
    # driver
    "DriverCreate", "DriverUpdate", "DriverProfileOut", "DriverOut",
    "DriverWithBusRoute", "DriverLoginResponse", "DriverListItem",
    # admin
    "AdminCreate", "AdminUpdate", "AdminProfileOut", "AdminOut",
    "AdminLoginResponse", "AdminListItem",
    # bus
    "BusCreate", "BusUpdate", "BusOut", "BusWithDetails",
    # route
    "StopCreate", "StopOut", "StopUpdate", "RouteCreate", "RouteUpdate",
    "RouteOut", "RouteListItem",
    # trip
    "TripStart", "TripStatusUpdate", "TripSeatUpdate", "TripOut",
    "TripWithDetails", "ETAResponse", "StopArrivalOut",
    # booking
    "BookingCreate", "BookingCancel", "BookingOut", "BookingWithDetails", "BookingStatusUpdate",
    # location
    "LocationUpdate", "LocationOut", "LiveBusOut", "NearestStopOut",
    # notification
    "NotificationSend", "BroadcastNotification", "NotificationOut", "NotificationMarkRead",
    # issue report
    "IssueReportCreate", "IssueReportOut", "IssueReportWithDetails", "IssueStatusUpdate",
    # audit log
    "AuditLogOut",
    # parent
    "ParentRegisterRequest", "ParentLoginResponse", "ParentUpdate", "ParentOut",
    "ChildLinkRequest", "ChildOut", "ChildTrackingOut", "ChildBookingStatusOut",
]
