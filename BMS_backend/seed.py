"""
Smart Bus Monitoring System - Database Seed Script
---------------------------------------------------
Run from BMS_backend root:
    venv\Scripts\activate
    python seed.py

Creates:
  • 1 Admin account
  • 1 Route (City Center → University) with 3 stops
  • 2 Buses assigned to the route
  • 2 Driver accounts
  • 3 Passenger accounts

Prints all credentials and UUIDs you need for testing.
"""

import asyncio
from app.database import AsyncSessionLocal, engine, Base
from app.models import *  # registers all models
from app.services.auth_service import hash_password


# ── Seed data ────────────────────────────────────────────────────────────────

ADMIN = {
    "full_name":    "System Admin",
    "email":        "admin@smartbus.com",
    "password":     "Admin@1234",
    "phone_number": "+923001111111",
    "department":   "Transport Management",
}

DRIVERS = [
    {
        "full_name":    "Ahmed Khan",
        "email":        "ahmed.driver@smartbus.com",
        "password":     "Driver@1234",
        "phone_number": "+923001234567",
        "driver_code":  "DRV-001",
        "license_number": "LHR-DL-2024-001",
    },
    {
        "full_name":    "Bilal Hussain",
        "email":        "bilal.driver@smartbus.com",
        "password":     "Driver@1234",
        "phone_number": "+923007654321",
        "driver_code":  "DRV-002",
        "license_number": "LHR-DL-2024-002",
    },
]

PASSENGERS = [
    {
        "full_name":    "Sara Ali",
        "email":        "sara@student.edu.pk",
        "password":     "Sara@1234",
        "phone_number": "+923119876543",
        "university_id": "2021-CS-001",
        "student_type":  "bscs",
        "department":    "Computer Science",
    },
    {
        "full_name":    "Fatima Malik",
        "email":        "fatima@student.edu.pk",
        "password":     "Fatima@1234",
        "phone_number": "+923331234567",
        "university_id": "2022-SE-005",
        "student_type":  "bsse",
        "department":    "Software Engineering",
    },
    {
        "full_name":    "Usman Shah",
        "email":        "usman@student.edu.pk",
        "password":     "Usman@1234",
        "phone_number": "+923214567890",
        "university_id": "2020-EE-012",
        "student_type":  "bsee",
        "department":    "Electrical Engineering",
    },
]

ROUTE = {
    "route_name":   "City Center Express",
    "route_number": "R-01",
    "start_point":  "City Center, Lahore",
    "end_point":    "University Main Gate",
    "distance_km":  12.5,
}

STOPS = [
    {"stop_name": "City Center",        "stop_order": 1, "latitude": 31.5204, "longitude": 74.3587, "estimated_minutes": 0},
    {"stop_name": "Gulberg Main Blvd",  "stop_order": 2, "latitude": 31.5120, "longitude": 74.3450, "estimated_minutes": 15},
    {"stop_name": "University Main Gate","stop_order": 3, "latitude": 31.4827, "longitude": 74.3015, "estimated_minutes": 35},
]

BUSES = [
    {"bus_number": "BUS-001", "capacity": 40, "model": "Toyota Coaster",  "plate_number": "LHR-1001"},
    {"bus_number": "BUS-002", "capacity": 35, "model": "Hino 300 Series", "plate_number": "LHR-1002"},
]


# ── Seed logic ────────────────────────────────────────────────────────────────

async def seed():
    from sqlalchemy import select, text

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure pgcrypto is available for gen_random_uuid()
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    async with AsyncSessionLocal() as db:
        print("\n" + "="*60)
        print("  SMART BUS MONITORING SYSTEM - DATABASE SEED")
        print("="*60)

        # ── Admin ──────────────────────────────────────────────────
        print("\n[1/5] Creating Admin account...")
        existing = await db.execute(select(User).where(User.email == ADMIN["email"]))
        if existing.scalar_one_or_none():
            print(f"      [!!] Admin already exists ({ADMIN['email']}), skipping.")
            admin_user = (await db.execute(select(User).where(User.email == ADMIN["email"]))).scalar_one()
        else:
            admin_user = User(
                full_name=ADMIN["full_name"],
                email=ADMIN["email"],
                password_hash=hash_password(ADMIN["password"]),
                role=UserRole.admin,
                phone_number=ADMIN["phone_number"],
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            await db.flush()
            db.add(Admin(admin_id=admin_user.id, department=ADMIN["department"], permissions={}))
            await db.commit()
            print(f"      [OK] Admin created: {ADMIN['email']}")

        # ── Route ──────────────────────────────────────────────────
        print("\n[2/5] Creating Route and Stops...")
        existing_route = await db.execute(select(Route).where(Route.route_number == ROUTE["route_number"]))
        route = existing_route.scalar_one_or_none()
        if route:
            print(f"      [!!] Route {ROUTE['route_number']} already exists, skipping.")
        else:
            route = Route(**ROUTE)
            db.add(route)
            await db.flush()
            for s in STOPS:
                db.add(Stop(route_id=route.id, **s))
            await db.commit()
            print(f"      [OK] Route '{ROUTE['route_name']}' created with {len(STOPS)} stops")

        # ── Buses ──────────────────────────────────────────────────
        print("\n[3/5] Creating Buses...")
        bus_ids = []
        for b in BUSES:
            existing_bus = await db.execute(select(Bus).where(Bus.bus_number == b["bus_number"]))
            if existing_bus.scalar_one_or_none():
                bus_obj = (await db.execute(select(Bus).where(Bus.bus_number == b["bus_number"]))).scalar_one()
                bus_ids.append(bus_obj.id)
                print(f"      [!!] Bus {b['bus_number']} already exists, skipping.")
            else:
                bus_obj = Bus(
                    bus_number=b["bus_number"],
                    capacity=b["capacity"],
                    available_seats=b["capacity"],
                    model=b["model"],
                    plate_number=b["plate_number"],
                    route_id=route.id,
                    is_active=True,
                )
                db.add(bus_obj)
                await db.flush()
                bus_ids.append(bus_obj.id)
                print(f"      [OK] Bus {b['bus_number']} created (capacity: {b['capacity']})")
        await db.commit()

        # ── Drivers ────────────────────────────────────────────────
        print("\n[4/5] Creating Driver accounts...")
        driver_ids = []
        for i, d in enumerate(DRIVERS):
            existing_drv = await db.execute(select(User).where(User.email == d["email"]))
            drv_user_existing = existing_drv.scalar_one_or_none()
            if drv_user_existing:
                drv_user = drv_user_existing
                driver_ids.append(drv_user.id)
                # Update bus linkage for existing drivers using raw SQL to avoid circular FK flush error
                if i < len(bus_ids):
                    await db.execute(
                        text("UPDATE drivers SET assigned_bus_id = :bid WHERE driver_id = :did"),
                        {"bid": bus_ids[i], "did": drv_user.id},
                    )
                    await db.execute(
                        text("UPDATE buses SET driver_id = :did WHERE id = :bid"),
                        {"did": drv_user.id, "bid": bus_ids[i]},
                    )
                    print(f"      [!!] Driver {d['email']} already exists - updated bus to {BUSES[i]['bus_number']}")
                else:
                    print(f"      [!!] Driver {d['email']} already exists, skipping.")
            else:
                drv_user = User(
                    full_name=d["full_name"],
                    email=d["email"],
                    password_hash=hash_password(d["password"]),
                    role=UserRole.driver,
                    phone_number=d["phone_number"],
                    is_active=True,
                    is_verified=True,
                )
                db.add(drv_user)
                await db.flush()
                drv = Driver(
                    driver_id=drv_user.id,
                    driver_code=d["driver_code"],
                    license_number=d["license_number"],
                    status=DriverStatus.offline,
                    assigned_bus_id=bus_ids[i] if i < len(bus_ids) else None,
                )
                db.add(drv)
                await db.flush()
                driver_ids.append(drv_user.id)
                # Also link bus → driver
                bus_obj = await db.get(Bus, bus_ids[i])
                if bus_obj and i < len(bus_ids):
                    bus_obj.driver_id = drv_user.id
                print(f"      [OK] Driver {d['driver_code']} ({d['full_name']}) → Bus {BUSES[i]['bus_number'] if i < len(BUSES) else '-'}")
        await db.commit()

        # ── Passengers ─────────────────────────────────────────────
        print("\n[5/5] Creating Passenger accounts...")
        for p in PASSENGERS:
            existing_pax = await db.execute(select(User).where(User.email == p["email"]))
            if existing_pax.scalar_one_or_none():
                print(f"      [!!] Passenger {p['email']} already exists, skipping.")
                continue
            pax_user = User(
                full_name=p["full_name"],
                email=p["email"],
                password_hash=hash_password(p["password"]),
                role=UserRole.passenger,
                phone_number=p["phone_number"],
                is_active=True,
                is_verified=True,
            )
            db.add(pax_user)
            await db.flush()
            db.add(Passenger(
                passenger_id=pax_user.id,
                university_id=p["university_id"],
                student_type=p["student_type"],
                department=p["department"],
                preferred_route_id=route.id,
            ))
            print(f"      [OK] Passenger {p['university_id']} ({p['full_name']}) created")
        await db.commit()

        # ── Print summary ──────────────────────────────────────────
        route_obj = (await db.execute(select(Route).where(Route.route_number == "R-01"))).scalar_one()
        buses_res = (await db.execute(select(Bus))).scalars().all()

        print("\n" + "="*60)
        print("  [OK]  SEED COMPLETE - CREDENTIALS SUMMARY")
        print("="*60)

        print("\n>> ROUTE")
        print(f"   ID    : {route_obj.id}")
        print(f"   Name  : {route_obj.route_name}")
        print(f"   Number: {route_obj.route_number}")

        print("\n>> BUSES")
        for b in buses_res:
            print(f"   {b.bus_number}  ID: {b.id}  Seats: {b.available_seats}/{b.capacity}")

        print("\n>> ADMIN")
        print(f"   Email   : {ADMIN['email']}")
        print(f"   Password: {ADMIN['password']}")

        print("\n>> DRIVERS  (login with driver_code + password)")
        for i, d in enumerate(DRIVERS):
            print(f"   [{d['driver_code']}] {d['full_name']}")
            print(f"         driver_code : {d['driver_code']}")
            print(f"         password    : {d['password']}")

        print("\n>> PASSENGERS  (login with email + password)")
        for p in PASSENGERS:
            print(f"   [{p['university_id']}] {p['full_name']}")
            print(f"         email       : {p['email']}")
            print(f"         password    : {p['password']}")

        print("\n" + "="*60)
        print("  Run the server:  uvicorn app.main:app --reload")
        print("  Swagger UI:      http://localhost:8000/docs")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())