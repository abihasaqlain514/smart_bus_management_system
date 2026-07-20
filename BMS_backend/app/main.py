import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os

from app.database import engine
from app.middleware.audit_middleware import AuditMiddleware
import app.models  # noqa: F401 — registers all ORM models with Base.metadata

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.database import Base, AsyncSessionLocal
    from app.services.trip_watchdog import trip_watchdog_loop

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Auto-seed routes/buses/drivers on every startup ─────────────────────
    # Fresh deployments (e.g. a new Replit DB) start with an empty database.
    # seed_university_routes.main() is idempotent — it upserts by
    # route_number / bus_number / email, so running it on every boot is safe
    # and keeps a redeployed backend populated without a manual step.
    # Set AUTO_SEED_ROUTES=false to disable.
    if os.getenv("AUTO_SEED_ROUTES", "true").lower() != "false":
        try:
            import seed_university_routes
            await seed_university_routes.main()
            log.info("Route auto-seed completed.")
        except Exception:
            log.exception("Route auto-seed failed — continuing startup without seeding.")

    watchdog = asyncio.create_task(
        trip_watchdog_loop(db_factory=AsyncSessionLocal),
        name="trip_watchdog",
    )

    yield

    watchdog.cancel()
    await engine.dispose()


app = FastAPI(
    title="Smart Bus Monitoring System",
    description=(
        "## How to authenticate in Swagger UI\n\n"
        "1. **Register** — call `POST /api/auth/passenger/register`, "
        "`POST /api/auth/driver/register`, or `POST /api/auth/admin/register`.\n"
        "2. **Login** — call the matching login endpoint and copy the `access_token` from the response.\n"
        "3. **Authorize** — click the **Authorize 🔒** button (top-right), "
        "paste your token in the **Value** field (no `Bearer` prefix needed), then click **Authorize**.\n"
        "4. All protected endpoints will now include your token automatically.\n\n"
        "Roles: `passenger` · `driver` · `admin` · `parent`"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Configuration ─────────────────────────────────────────────────────────
#
# Production: Restrict to known domains (Replit frontend + any other trusted origins)
# Development: Allow localhost for local testing
#
# Environment variable format:
#   ALLOWED_ORIGINS = https://frontend.replit.dev,https://backend.replit.dev,http://localhost:3000
#
# If not set, defaults to localhost for development
#
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://localhost:8081,http://127.0.0.1:8000"
)
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.add_middleware(AuditMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers import (
    auth, passenger, parent, driver, admin,
    buses, routes, trips, bookings, locations, notifications, debug,
)

app.include_router(auth.router,          prefix="/api")
app.include_router(passenger.router,     prefix="/api")
app.include_router(parent.router,        prefix="/api")
app.include_router(driver.router,        prefix="/api")
app.include_router(admin.router,         prefix="/api")
app.include_router(buses.router,         prefix="/api")
app.include_router(routes.router,        prefix="/api")
app.include_router(trips.router,         prefix="/api")
app.include_router(bookings.router,      prefix="/api")
app.include_router(locations.router,     prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(debug.router,         prefix="/api")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "Smart Bus Monitoring System is running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


# ── Custom OpenAPI — adds Bearer security scheme ──────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your JWT token (without 'Bearer' prefix)",
        }
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
