from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps import require_admin, get_current_user
from app.models.route import Route, Stop
from app.schemas.route import RouteCreate, RouteUpdate, RouteOut, StopCreate, StopOut

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/", response_model=List[RouteOut])
async def list_routes(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Route).where(Route.is_active == True))
    return result.scalars().all()


@router.get("/{route_id}", response_model=RouteOut)
async def get_route(route_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/{route_id}/stops", response_model=List[StopOut])
async def get_route_stops(route_id: UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Stop).where(Stop.route_id == route_id).order_by(Stop.stop_order)
    )
    return result.scalars().all()


@router.post("/", response_model=RouteOut)
async def create_route(data: RouteCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    existing = await db.execute(select(Route).where(Route.route_number == data.route_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Route number already exists")

    route = Route(**data.model_dump())
    db.add(route)
    await db.commit()
    await db.refresh(route)

    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="CREATE_ROUTE",
        table_name="routes",
        record_id=str(route.id),
        new_value=data.model_dump(),
    ))
    await db.commit()
    return route


@router.post("/{route_id}/stops", response_model=StopOut)
async def add_stop(route_id: UUID, data: StopCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Route not found")

    stop = Stop(route_id=route_id, **data.model_dump())
    db.add(stop)
    await db.commit()
    await db.refresh(stop)
    return stop


@router.put("/{route_id}", response_model=RouteOut)
async def update_route(route_id: UUID, data: RouteUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(route, field, value)

    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="UPDATE_ROUTE",
        table_name="routes",
        record_id=str(route_id),
        new_value=data.model_dump(exclude_none=True),
    ))
    await db.commit()
    await db.refresh(route)
    return route


@router.delete("/{route_id}")
async def delete_route(route_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.is_active = False
    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        admin_id=admin.admin_profile.admin_id,
        action="DELETE_ROUTE",
        table_name="routes",
        record_id=str(route_id),
    ))
    await db.commit()
    return {"message": "Route deactivated"}
