"""
Cleanup: deactivate old non-Jhang buses and routes.
Keeps only JHG-001, JHG-002, JHG-003 and R-JHG-* routes active.
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.begin() as conn:
        # Deactivate all old buses (non-JHG)
        r1 = await conn.execute(text("""
            UPDATE buses SET is_active=false, status='not_in_service'
            WHERE bus_number NOT LIKE 'JHG-%'
        """))
        print(f"Deactivated {r1.rowcount} old buses")

        # Deactivate all old routes (non-JHG)
        r2 = await conn.execute(text("""
            UPDATE routes SET is_active=false
            WHERE route_number NOT LIKE 'R-JHG-%'
        """))
        print(f"Deactivated {r2.rowcount} old routes")

        # End any stale active trips from old buses
        r3 = await conn.execute(text("""
            UPDATE trips SET status='completed', ended_at=now()
            WHERE status='active'
              AND bus_id NOT IN (
                SELECT id FROM buses WHERE bus_number LIKE 'JHG-%'
              )
        """))
        print(f"Closed {r3.rowcount} stale trips")

        # Clean driver assignments from old buses
        r4 = await conn.execute(text("""
            UPDATE drivers SET assigned_bus_id=NULL, status='available'
            WHERE assigned_bus_id IS NOT NULL
              AND assigned_bus_id NOT IN (
                SELECT id FROM buses WHERE bus_number LIKE 'JHG-%'
              )
        """))
        print(f"Cleared {r4.rowcount} old driver-bus assignments")

        # Make JHG buses active
        r5 = await conn.execute(text("""
            UPDATE buses SET is_active=true
            WHERE bus_number LIKE 'JHG-%'
        """))
        print(f"Activated {r5.rowcount} JHG buses")

        # Make JHG routes active
        r6 = await conn.execute(text("""
            UPDATE routes SET is_active=true
            WHERE route_number LIKE 'R-JHG-%'
        """))
        print(f"Activated {r6.rowcount} JHG routes")

    print("Cleanup done")

asyncio.run(main())
