import asyncio
from sqlalchemy import text
from app.database import engine

async def show():
    async with engine.connect() as c:
        print("=== BUSES ===")
        rows = (await c.execute(text(
            "SELECT bus_number, id, route_id, driver_id, status FROM buses ORDER BY bus_number"
        ))).fetchall()
        for r in rows:
            print(f"  {r[0]}  id={r[1]}  route={r[2]}  driver={r[3]}  status={r[4]}")

        print("\n=== ROUTES ===")
        rows = (await c.execute(text(
            "SELECT route_number, route_name, id FROM routes ORDER BY route_number"
        ))).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]}  id={r[2]}")

        print("\n=== DRIVERS (JHG) ===")
        rows = (await c.execute(text(
            "SELECT d.driver_code, u.email, u.id, d.assigned_bus_id "
            "FROM drivers d JOIN users u ON u.id=d.driver_id "
            "ORDER BY d.driver_code"
        ))).fetchall()
        for r in rows:
            print(f"  {r[0]}  email={r[1]}  id={r[2]}  bus={r[3]}")

asyncio.run(show())
