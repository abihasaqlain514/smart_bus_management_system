"""Delete GPS location records outside Pakistan (Mountain View CA etc.)."""
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            DELETE FROM bus_locations
            WHERE latitude NOT BETWEEN 23.5 AND 37.5
               OR longitude NOT BETWEEN 60.8 AND 77.8
        """))
        print(f"Deleted {result.rowcount} non-Pakistan GPS records")

asyncio.run(main())
