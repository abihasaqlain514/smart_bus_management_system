"""Run once: adds gender column to passengers table."""
import asyncio
from sqlalchemy import text
from app.database import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE passengers ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT 'other'"
        ))
        print("OK: gender column ready")

    # Verify
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name='passengers' AND column_name='gender'"
        ))
        row = result.fetchone()
        if row:
            print("VERIFIED: column exists -", row)
        else:
            print("WARNING: column not found")


if __name__ == "__main__":
    asyncio.run(main())
