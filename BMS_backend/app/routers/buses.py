from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps import require_admin, require_passenger, get_current_user
from app.models.bus import Bus
from app.services.gps_service import get_latest_bus_location
from app.schemas.bus import BusCreate, BusUpdate, BusOut
from app.schemas.location import LocationOut

router = APIRouter(prefix="/buses", tags=["buses"])


@router.get("/", response_model=List[BusOut])
async def list_buses(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Bus).where(Bus.is_active == True))
    return result.scalars().all()


@router.get("/{bus_id}/location", response_model=LocationOut)
async def get_bus_location(bus_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    location = await get_latest_bus_location(db, bus_id)
    if not location:
        raise HTTPException(status_code=404, detail="No location data for this bus")
    return location


@router.get("/{bus_id}/seats")
async def get_bus_seats(bus_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Bus).where(Bus.id == bus_id, Bus.is_active == True))
    bus = result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    return {"bus_id": bus_id, "available_seats": bus.available_seats, "capacity": bus.capacity}


@router.post("/", response_model=BusOut)
async def create_bus(data: BusCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    existing = await db.execute(select(Bus).where(Bus.bus_number == data.bus_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bus number already exists")

    bus = Bus(
        bus_number=data.bus_number,
        capacity=data.capacity,
        available_seats=data.capacity,
        route_id=data.route_id,
        model=data.model,
        plate_number=data.plate_number,
    )
    db.add(bus)
    await db.commit()
    await db.refresh(bus)

    # Audit log
    from app.models.audit_log import AuditLog
    audit = AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="CREATE_BUS",
        table_name="buses",
        record_id=str(bus.id),
        new_value={"bus_number": data.bus_number},
    )
    db.add(audit)
    await db.commit()
    return bus


@router.put("/{bus_id}", response_model=BusOut)
async def update_bus(bus_id: UUID, data: BusUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    old = {"status": str(bus.status), "available_seats": bus.available_seats}
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bus, field, value)

    from app.models.audit_log import AuditLog
    audit = AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="UPDATE_BUS",
        table_name="buses",
        record_id=str(bus_id),
        old_value=old,
        new_value=data.model_dump(exclude_none=True),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(bus)
    return bus


@router.delete("/{bus_id}")
async def delete_bus(bus_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    bus.is_active = False

    from app.models.audit_log import AuditLog
    audit = AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="DELETE_BUS",
        table_name="buses",
        record_id=str(bus_id),
    )
    db.add(audit)
    await db.commit()
    return {"message": "Bus deactivated"}
