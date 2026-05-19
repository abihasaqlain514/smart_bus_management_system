"""Reset stale on_route/on_trip statuses that have no active trip."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine

async def main():
    async with AsyncSession(engine) as db:
        r1 = await db.execute(text(
            "UPDATE buses SET status='not_in_service' "
            "WHERE status='on_route' "
            "AND id NOT IN (SELECT bus_id FROM trips WHERE status='active')"
        ))
        r2 = await db.execute(text(
            "UPDATE drivers SET status='available', is_online=false "
            "WHERE status='on_trip' "
            "AND driver_id NOT IN (SELECT driver_id FROM trips WHERE status='active')"
        ))
        await db.commit()
        print(f"Reset {r1.rowcount} stale bus(es), {r2.rowcount} stale driver(s)")

asyncio.run(main())
