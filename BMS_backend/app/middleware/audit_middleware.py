from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuditMiddleware(BaseHTTPMiddleware):
    """Attaches client IP to request state for audit log use."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        request.state.client_ip = client_ip
        response = await call_next(request)
        return response
