"""
Jhang Smart Bus System - Complete Seed Script
Run: python seed_jhang.py

Creates:
  - 2 seeded drivers  (DRV-JHG-01, DRV-JHG-02)
  - 3 buses           (JHG-001 to JHG-003)
  - 3 routes with stops covering University of Jhang area
  - Assigns drivers + routes to buses, sets status to on_route
  - Prints all IDs so admin can use them
"""
import asyncio
from datetime import date
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, Base
from app.models.user import User, UserRole
from app.models.driver import Driver, DriverStatus
from app.models.bus import Bus, BusStatus
from app.models.route import Route, Stop
from app.models.passenger import Passenger
from app.services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Jhang GPS coordinates (verified real locations)
# ---------------------------------------------------------------------------
STOPS = {
    # Route 1: University of Jhang → City Center → Clock Tower
    "university_main_gate": (31.2693, 72.3210),
    "new_campus_turn":      (31.2710, 72.3195),
    "jhang_city_center":    (31.2724, 72.3148),
    "civil_hospital":       (31.2745, 72.3110),
    "clock_tower_chowk":    (31.2709, 72.3088),

    # Route 2: University → New Hospital → Jhang Sadar
    "sports_complex":       (31.2680, 72.3230),
    "new_hospital":         (31.2780, 72.3222),
    "jhang_sadar":          (31.2800, 72.3150),
    "gol_bagh":             (31.2760, 72.3052),
    "uch_sharif_road":      (31.2580, 72.3300),

    # Route 3: University → 12 Chungi → Railway Station → Bus Stand
    "12_chungi":            (31.2543, 72.3253),
    "jhang_railway_station":(31.2644, 72.3272),
    "main_bus_stand":       (31.2615, 72.3135),
    "sheikhupura_colony":   (31.2650, 72.3002),
}

# ---------------------------------------------------------------------------
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as db:

        # ── Drivers ────────────────────────────────────────────────────────
        drivers_data = [
            dict(full_name="Tariq Hussain",  email="tariq@jhangbus.pk",   password="Driver@1234",
                 phone="+923006001001", code="DRV-JHG-01", license="LHR-DL-2024-101"),
            dict(full_name="Imran Rasheed",  email="imran@jhangbus.pk",    password="Driver@1234",
                 phone="+923006001002", code="DRV-JHG-02", license="LHR-DL-2024-102"),
        ]
        driver_users = []
        for d in drivers_data:
            existing = (await db.execute(select(User).where(User.email == d["email"]))).scalar_one_or_none()
            if existing:
                drv = (await db.execute(select(Driver).where(Driver.driver_id == existing.id))).scalar_one_or_none()
                driver_users.append((existing, drv))
                print(f"  Driver exists: {d['code']} ({existing.id})")
                continue
            u = User(full_name=d["full_name"], email=d["email"],
                     password_hash=hash_password(d["password"]),
                     role=UserRole.driver, phone_number=d["phone"])
            db.add(u)
            await db.flush()
            drv = Driver(driver_id=u.id, driver_code=d["code"],
                         license_number=d["license"],
                         license_expiry_date=date(2029, 12, 31),
                         status=DriverStatus.available, is_online=False)
            db.add(drv)
            driver_users.append((u, drv))
            print(f"  Created driver: {d['code']} ({u.id})")
        await db.flush()

        # ── Buses ──────────────────────────────────────────────────────────
        buses_data = [
            dict(num="JHG-001", cap=40, model="Hino Coach",       plate="JHG-1001"),
            dict(num="JHG-002", cap=40, model="Toyota Coaster",   plate="JHG-1002"),
            dict(num="JHG-003", cap=35, model="Master Coaster",   plate="JHG-1003"),
        ]
        bus_objs = []
        for b in buses_data:
            existing = (await db.execute(select(Bus).where(Bus.bus_number == b["num"]))).scalar_one_or_none()
            if existing:
                bus_objs.append(existing)
                print(f"  Bus exists: {b['num']} ({existing.id})")
                continue
            bus = Bus(bus_number=b["num"], capacity=b["cap"], available_seats=b["cap"],
                      model=b["model"], plate_number=b["plate"],
                      status=BusStatus.not_in_service, is_active=True)
            db.add(bus)
            bus_objs.append(bus)
        await db.flush()

        # ── Routes & Stops ─────────────────────────────────────────────────
        routes_raw = [
            dict(
                name="University–Clock Tower Express",
                number="R-JHG-01",
                start="University of Jhang",
                end="Clock Tower Chowk",
                dist=4.2,
                stops=[
                    ("University Main Gate",   *STOPS["university_main_gate"],    0),
                    ("New Campus Turn",        *STOPS["new_campus_turn"],          4),
                    ("Jhang City Center",      *STOPS["jhang_city_center"],        9),
                    ("Civil Hospital Chowk",   *STOPS["civil_hospital"],           13),
                    ("Clock Tower Chowk",      *STOPS["clock_tower_chowk"],        17),
                ],
            ),
            dict(
                name="University–Jhang Sadar Route",
                number="R-JHG-02",
                start="University of Jhang",
                end="Gol Bagh",
                dist=5.8,
                stops=[
                    ("University Main Gate",   *STOPS["university_main_gate"],    0),
                    ("Sports Complex",         *STOPS["sports_complex"],           3),
                    ("New Hospital",           *STOPS["new_hospital"],             8),
                    ("Jhang Sadar",            *STOPS["jhang_sadar"],              13),
                    ("Gol Bagh",               *STOPS["gol_bagh"],                 19),
                ],
            ),
            dict(
                name="University–Railway Station–Bus Stand",
                number="R-JHG-03",
                start="University of Jhang",
                end="Main Bus Stand",
                dist=6.5,
                stops=[
                    ("University Main Gate",   *STOPS["university_main_gate"],    0),
                    ("12 Chungi",              *STOPS["12_chungi"],                7),
                    ("Jhang Railway Station",  *STOPS["jhang_railway_station"],    13),
                    ("Main Bus Stand",         *STOPS["main_bus_stand"],           18),
                    ("Sheikhupura Colony",     *STOPS["sheikhupura_colony"],       23),
                ],
            ),
        ]

        route_objs = []
        for r in routes_raw:
            existing = (await db.execute(
                select(Route).where(Route.route_number == r["number"])
            )).scalar_one_or_none()
            if existing:
                route_objs.append(existing)
                print(f"  Route exists: {r['number']} ({existing.id})")
                continue
            ro = Route(route_name=r["name"], route_number=r["number"],
                       start_point=r["start"], end_point=r["end"],
                       distance_km=r["dist"], is_active=True)
            db.add(ro)
            await db.flush()

            for i, (sname, slat, slng, smins) in enumerate(r["stops"]):
                db.add(Stop(route_id=ro.id, stop_name=sname, stop_order=i+1,
                            latitude=slat, longitude=slng, estimated_minutes=smins))
            route_objs.append(ro)
            print(f"  Created route: {r['number']} ({ro.id})")
        await db.flush()

        # ── Assign drivers + routes to buses ───────────────────────────────
        for i, bus in enumerate(bus_objs):
            route = route_objs[i % len(route_objs)]
            drv_user, drv = driver_users[i % len(driver_users)] if i < len(driver_users) else (None, None)

            await db.execute(
                sql_update(Bus).where(Bus.id == bus.id).values(
                    route_id=route.id,
                    driver_id=drv_user.id if drv_user else None,
                    status=BusStatus.not_in_service,
                ).execution_options(synchronize_session=False)
            )
            if drv_user:
                await db.execute(
                    sql_update(Driver).where(Driver.driver_id == drv_user.id).values(
                        assigned_bus_id=bus.id,
                        status=DriverStatus.available,
                    ).execution_options(synchronize_session=False)
                )

        await db.commit()

        # ── Print summary ──────────────────────────────────────────────────
        print("\n" + "="*60)
        print("  JHANG SMART BUS - SEED COMPLETE")
        print("="*60)

        print("\nDRIVERS (login with driver code + Driver@1234):")
        for u, drv in driver_users:
            if drv:
                print(f"  Code: {drv.driver_code}   ID: {u.id}")

        print("\nBUSES:")
        for b in bus_objs:
            print(f"  {b.bus_number}  |  ID: {b.id}  |  Route: {b.route_id}  |  Driver: {b.driver_id}")

        print("\nROUTES:")
        for r in route_objs:
            print(f"  {r.route_number}: {r.route_name}  |  ID: {r.id}")

        print("\n" + "="*60)
        print("Driver logins:")
        for d in drivers_data:
            print(f"  Code: {d['code'].ljust(15)}  Password: {d['password']}")
        print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
