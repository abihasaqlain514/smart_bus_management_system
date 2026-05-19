"""Migration: add stop_time column to stops table. Run once."""
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE stops ADD COLUMN IF NOT EXISTS stop_time VARCHAR(10)"
        ))
    print("Migration done: stops.stop_time added")

asyncio.run(main())
