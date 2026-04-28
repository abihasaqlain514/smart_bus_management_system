from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

UNPROTECTED_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/passenger/register",
    "/api/auth/passenger/login",
    "/api/auth/driver/login",
    "/api/auth/admin/login",
    "/ws/live-tracking",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in UNPROTECTED_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        return await call_next(request)
