from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.auth_service import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_passenger(current_user=Depends(get_current_user)):
    from app.models.user import UserRole

    if current_user.role != UserRole.passenger:
        raise HTTPException(status_code=403, detail="Passenger access required")
    return current_user


async def require_driver(current_user=Depends(get_current_user)):
    from app.models.user import UserRole

    if current_user.role != UserRole.driver:
        raise HTTPException(status_code=403, detail="Driver access required")
    return current_user


async def require_admin(current_user=Depends(get_current_user)):
    from app.models.user import UserRole

    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_parent(current_user=Depends(get_current_user)):
    from app.models.user import UserRole

    if current_user.role != UserRole.parent:
        raise HTTPException(status_code=403, detail="Parent access required")
    return current_user
