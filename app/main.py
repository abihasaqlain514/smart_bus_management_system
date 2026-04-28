from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.middleware.audit_middleware import AuditMiddleware

# Import all models so SQLAlchemy registers them before create_all
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Smart Bus Monitoring System",
    description="Backend API for real-time bus tracking, booking, and fleet management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — open for React Native dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# Routers
from app.routers import auth, passenger, driver, admin, buses, routes, trips, bookings, locations, notifications
from app.routers import parent

app.include_router(auth.router, prefix="/api")
app.include_router(passenger.router, prefix="/api")
app.include_router(driver.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(parent.router, prefix="/api")
app.include_router(buses.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(trips.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")

# WebSocket live-tracking endpoint (also registered in locations router at /ws path)
# The WebSocket route is declared inside locations.router — no extra mount needed


@app.get("/")
async def root():
    return {"status": "Smart Bus Monitoring System is running", "docs": "/docs"}
