from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.database import engine
from app.middleware.audit_middleware import AuditMiddleware
import app.models  # noqa: F401 — registers all ORM models with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.database import Base, AsyncSessionLocal
    from app.services.trip_watchdog import trip_watchdog_loop

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

# ── CORS — open for React Native dev; tighten origins in production ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
