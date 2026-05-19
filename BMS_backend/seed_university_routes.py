"""
University of Jhang - Official Bus Routes Seed
================================================
Seeds all 10 real routes with authentic stops, scheduled times, GPS coordinates,
and assigns buses. Run ONCE after running add_stop_time.py migration.

  python seed_university_routes.py

Routes:   1-M to 11-M  (Route 10-M not in schedule)
Buses:    101, 215, 216, 300 (official) + 400,500,600,800,900,111 for remaining
Drivers:  DRV-JHG-01, DRV-JHG-02 (pre-seeded); 8 new drivers added here
All routes end at: University of Jhang (31.2693, 72.3210) at 8:00
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
from app.services.auth_service import hash_password

# ── University destination (last stop on every route) ──────────────────────
UNIV = (31.2693, 72.3210)

# ── All 10 routes with stops, times, GPS ───────────────────────────────────
ROUTES = [
    {
        "name": "Route 1-M | Chowkidar Ki Hatti -> University",
        "number": "1-M",
        "bus_number": "101",
        "start": "Chowkidar Ki Hatti",
        "end": "University of Jhang",
        "distance_km": 12.5,
        "stops": [
            ("Chowkidar Ki Hatti",   31.2895, 72.3310, "7:00",  0),
            ("Ali Abad",             31.2870, 72.3295, "7:10", 10),
            ("Bhakhar Chowngi",      31.2840, 72.3280, "7:15", 15),
            ("Gandaa Toyaa",         31.2805, 72.3265, "7:20", 20),
            ("Ayoub Chowk",          31.2765, 72.3255, "7:25", 25),
            ("Faisalabad Road",      31.2720, 72.3375, "7:30", 30),
            ("Chiniot Mor",          31.2665, 72.3275, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 2-M | Sadar Chowk -> University",
        "number": "2-M",
        "bus_number": "215",
        "start": "Sadar Chowk",
        "end": "University of Jhang",
        "distance_km": 9.8,
        "stops": [
            ("Sadar Chowk",          31.2800, 72.3150, "7:00",  0),
            ("Fawara Chowk",         31.2778, 72.3098, "7:10", 10),
            ("Rail Bazaar",          31.2758, 72.3080, "7:15", 15),
            ("Sabzi Mandi",          31.2738, 72.3068, "7:20", 20),
            ("Adhiwal Chowk",        31.2720, 72.3118, "7:25", 25),
            ("Sargodha Bypass",      31.2700, 72.3155, "7:30", 30),
            ("Sufi Mor",             31.2678, 72.3248, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 3-M | Burji Chowk -> University",
        "number": "3-M",
        "bus_number": "216",
        "start": "Burji Chowk",
        "end": "University of Jhang",
        "distance_km": 14.2,
        "stops": [
            ("Burji Chowk",          31.2905, 72.3505, "7:00",  0),
            ("Lalazar",              31.2882, 72.3462, "7:10", 10),
            ("Toba Bypass",          31.2852, 72.3432, "7:15", 15),
            ("Gojra Bypass",         31.2822, 72.3402, "7:20", 20),
            ("Kot Lakhnana",         31.2790, 72.3368, "7:25", 25),
            ("Faisalabad Bypass",    31.2742, 72.3332, "7:30", 30),
            ("Sufi Mor",             31.2678, 72.3248, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 4-M | Excise Office -> University",
        "number": "4-M",
        "bus_number": "400",
        "start": "Excise Office",
        "end": "University of Jhang",
        "distance_km": 8.6,
        "stops": [
            ("Excise Office",        31.2762, 72.3048, "7:00",  0),
            ("Kapahi Mohallah",      31.2742, 72.3068, "7:10", 10),
            ("Ayoub Chowk",          31.2765, 72.3255, "7:15", 15),
            ("Rasheed Chowk",        31.2732, 72.3188, "7:20", 20),
            ("Jhang City",           31.2709, 72.3088, "7:25", 25),
            ("Adhiwal Chowk",        31.2720, 72.3118, "7:30", 30),
            ("Amir Town",            31.2700, 72.3158, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 5-M | Saddique Abad -> University",
        "number": "5-M",
        "bus_number": "500",
        "start": "Saddique Abad",
        "end": "University of Jhang",
        "distance_km": 7.4,
        "stops": [
            ("Saddique Abad",        31.2582, 72.3098, "7:00",  0),
            ("Main Gate",            31.2612, 72.3128, "7:10", 10),
            ("Riaz Chowk",           31.2632, 72.3158, "7:15", 15),
            ("Bashir Chowk",         31.2645, 72.3188, "7:20", 20),
            ("Musa Chowk",           31.2658, 72.3215, "7:25", 25),
            ("Wah Wali Chungi",      31.2660, 72.3248, "7:30", 30),
            ("Chiniot Mor",          31.2665, 72.3275, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 6-M | Faisalabad Phatak -> University",
        "number": "6-M",
        "bus_number": "600",
        "start": "Faisalabad Phatak",
        "end": "University of Jhang",
        "distance_km": 10.1,
        "stops": [
            ("Faisalabad Phatak",    31.2592, 72.3362, "7:00",  0),
            ("Dar-ul-Sakina Phatak", 31.2612, 72.3342, "7:10", 10),
            ("Al-Hayat Garden",      31.2632, 72.3322, "7:15", 15),
            ("Dhudhi Mor",           31.2645, 72.3302, "7:20", 20),
            ("Jhang Palace",         31.2658, 72.3285, "7:25", 25),
            ("Chiniot Mor",          31.2665, 72.3275, "7:30", 30),
            ("Sufi Mor",             31.2678, 72.3248, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 7-M | Syed Wala -> University",
        "number": "7-M",
        "bus_number": "300",
        "start": "Syed Wala",
        "end": "University of Jhang",
        "distance_km": 22.0,
        "stops": [
            ("Syed Wala",            31.3002, 72.3602, "7:00",  0),
            ("Moza Bagh",            31.2952, 72.3552, "7:10", 10),
            ("Toba Bypass",          31.2852, 72.3432, "7:15", 15),
            ("Gojra Bypass",         31.2822, 72.3402, "7:20", 20),
            ("Faisalabad Bypass",    31.2742, 72.3332, "7:25", 25),
            ("Sufi Mor",             31.2678, 72.3248, "7:45", 45),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 8-M | Abbot Pur -> University",
        "number": "8-M",
        "bus_number": "800",
        "start": "Abbot Pur Chowk",
        "end": "University of Jhang",
        "distance_km": 16.3,
        "stops": [
            ("Abbot Pur Chowk",       31.2492, 72.3452, "7:00",  0),
            ("Khatm-e-Nabuwat Chowk", 31.2522, 72.3432, "7:10", 10),
            ("Gojra Road",            31.2552, 72.3402, "7:15", 15),
            ("Gojra Phatak",          31.2582, 72.3385, "7:20", 20),
            ("Bilquis Clinic",        31.2602, 72.3368, "7:25", 25),
            ("Baig Colony",           31.2622, 72.3348, "7:30", 30),
            ("Jamia Chowk",           31.2642, 72.3318, "7:40", 40),
            ("Chiniot Mor",           31.2665, 72.3275, "7:50", 50),
            ("University of Jhang",   *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 9-M | Gojra Phatak -> University",
        "number": "9-M",
        "bus_number": "900",
        "start": "Gojra Phatak",
        "end": "University of Jhang",
        "distance_km": 11.8,
        "stops": [
            ("Gojra Phatak",         31.2582, 72.3385, "7:00",  0),
            ("Gojra Road",           31.2552, 72.3402, "7:10", 10),
            ("Kalma Chowk",          31.2602, 72.3342, "7:15", 15),
            ("Bashir Chowk",         31.2645, 72.3188, "7:20", 20),
            ("Goga Chowk",           31.2660, 72.3212, "7:25", 25),
            ("Lalazaar",             31.2672, 72.3240, "7:30", 30),
            ("Chiniot Mor",          31.2665, 72.3275, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
    {
        "name": "Route 11-M | Abbot Pur (via Farooq-e-Azam) -> University",
        "number": "11-M",
        "bus_number": "111",
        "start": "Abbot Pur Chowk",
        "end": "University of Jhang",
        "distance_km": 13.5,
        "stops": [
            ("Abbot Pur Chowk",      31.2492, 72.3452, "7:00",  0),
            ("Tarzan Chowk",         31.2512, 72.3415, "7:10", 10),
            ("Bulaak Shah",          31.2532, 72.3382, "7:15", 15),
            ("Laila Majnu Gate",     31.2552, 72.3352, "7:20", 20),
            ("Mout Wali Gali",       31.2572, 72.3322, "7:25", 25),
            ("Bhabhrana Muhallah",   31.2602, 72.3292, "7:30", 30),
            ("Farooq-e-Azam Road",   31.2642, 72.3262, "7:40", 40),
            ("University of Jhang",  *UNIV,            "8:00", 60),
        ],
    },
]

# ── Drivers for each route (1 driver per bus) ──────────────────────────────
DRIVER_DATA = [
    ("Tariq Hussain",   "tariq@jhangbus.pk",   "DRV-JHG-01"),   # route 1-M bus 101
    ("Imran Rasheed",   "imran@jhangbus.pk",   "DRV-JHG-02"),   # route 2-M bus 215
    ("Shahzad Ahmed",   "shahzad@jhangbus.pk", "DRV-JHG-03"),   # route 3-M bus 216
    ("Nasir Iqbal",     "nasir@jhangbus.pk",   "DRV-JHG-04"),   # route 4-M bus 400
    ("Umar Farooq",     "umar@jhangbus.pk",    "DRV-JHG-05"),   # route 5-M bus 500
    ("Bilal Aslam",     "bilal@jhangbus.pk",   "DRV-JHG-06"),   # route 6-M bus 600
    ("Asif Mehmood",    "asif@jhangbus.pk",    "DRV-JHG-07"),   # route 7-M bus 300
    ("Zulfiqar Ali",    "zulfiqar@jhangbus.pk","DRV-JHG-08"),   # route 8-M bus 800
    ("Fawad Hussain",   "fawad@jhangbus.pk",   "DRV-JHG-09"),   # route 9-M bus 900
    ("Junaid Khan",     "junaid@jhangbus.pk",  "DRV-JHG-10"),   # route 11-M bus 111
]


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as db:

        # ── Deactivate old demo routes/buses ──────────────────────────────
        from sqlalchemy import text
        await db.execute(text("UPDATE routes SET is_active=false WHERE route_number NOT LIKE '%-M'"))
        await db.execute(text("UPDATE buses  SET is_active=false WHERE bus_number  LIKE 'JHG-%'"))
        await db.commit()
        print("Cleared old demo data.")

        # ── Create / ensure drivers ────────────────────────────────────────
        driver_map = {}  # driver_code -> driver_id (User.id)
        for full_name, email, code in DRIVER_DATA:
            existing_user = (await db.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()

            if existing_user:
                driver_map[code] = existing_user.id
                print(f"  Driver exists: {code}")
                continue

            u = User(
                full_name=full_name, email=email,
                password_hash=hash_password("Driver@1234"),
                role=UserRole.driver, phone_number=f"+9230060{DRIVER_DATA.index((full_name, email, code)):05d}",
            )
            db.add(u)
            await db.flush()

            drv = Driver(
                driver_id=u.id, driver_code=code,
                license_number=f"LHR-DL-2025-{code[-2:]}",
                license_expiry_date=date(2030, 12, 31),
                status=DriverStatus.available, is_online=False,
            )
            db.add(drv)
            driver_map[code] = u.id
            print(f"  Created driver: {code} - {full_name}")
        await db.flush()

        # ── Create routes, stops, buses ───────────────────────────────────
        for i, rd in enumerate(ROUTES):
            # Route
            existing_route = (await db.execute(
                select(Route).where(Route.route_number == rd["number"])
            )).scalar_one_or_none()

            if existing_route:
                ro = existing_route
                ro.is_active = True
                ro.route_name = rd["name"]
                await db.flush()
                # Delete old stops to re-seed clean
                await db.execute(
                    text(f"DELETE FROM stops WHERE route_id='{ro.id}'")
                )
                print(f"  Route exists (updated): {rd['number']}")
            else:
                ro = Route(
                    route_name=rd["name"],
                    route_number=rd["number"],
                    start_point=rd["start"],
                    end_point=rd["end"],
                    distance_km=rd["distance_km"],
                    is_active=True,
                )
                db.add(ro)
                await db.flush()
                print(f"  Created route: {rd['number']} - {rd['name']}")

            # Stops
            for order, (sname, slat, slng, stime, smins) in enumerate(rd["stops"], start=1):
                db.add(Stop(
                    route_id=ro.id,
                    stop_name=sname,
                    stop_order=order,
                    latitude=slat,
                    longitude=slng,
                    stop_time=stime,
                    estimated_minutes=smins,
                ))
            await db.flush()

            # Bus
            bus_num = rd["bus_number"]
            existing_bus = (await db.execute(
                select(Bus).where(Bus.bus_number == bus_num)
            )).scalar_one_or_none()

            if existing_bus:
                b = existing_bus
                b.is_active = True
                b.route_id = ro.id
                await db.flush()
                print(f"  Bus exists (activated): {bus_num}")
            else:
                b = Bus(
                    bus_number=bus_num,
                    capacity=40,
                    available_seats=40,
                    model="University Coach",
                    plate_number=f"JHG-{bus_num}",
                    status=BusStatus.not_in_service,
                    is_active=True,
                    route_id=ro.id,
                )
                db.add(b)
                await db.flush()
                print(f"  Created bus: {bus_num}")

            # Assign driver (round-robin for now)
            drv_code = DRIVER_DATA[i % len(DRIVER_DATA)][2]
            drv_user_id = driver_map[drv_code]
            b.driver_id = drv_user_id
            await db.execute(
                sql_update(Driver)
                .where(Driver.driver_id == drv_user_id)
                .values(assigned_bus_id=b.id, status=DriverStatus.available)
                .execution_options(synchronize_session=False)
            )

        await db.commit()

        # ── Summary ───────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("  UNIVERSITY OF JHANG - BUS ROUTES SEEDED")
        print("=" * 65)
        print(f"\n  {len(ROUTES)} routes | {len(DRIVER_DATA)} drivers | {len(ROUTES)} buses")
        print("\n  All drivers login with: <driver_code> / Driver@1234")
        print("\n  Routes:")
        for rd in ROUTES:
            print(f"    {rd['number']:6s}  Bus {rd['bus_number']:5s}  {rd['start']:30s} -> {rd['end']}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
