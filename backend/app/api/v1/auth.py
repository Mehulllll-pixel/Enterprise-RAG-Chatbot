from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from pydantic import BaseModel

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.user import LoginRequest, Token
from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Authenticate credentials and generate access/refresh tokens."""
    auth_service = AuthService(db, redis)
    return await auth_service.login(credentials)

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Re-issue access token using a valid refresh token."""
    auth_service = AuthService(db, redis)
    return await auth_service.refresh_session(payload.refresh_token)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Revoke refresh token and invalidate user session."""
    auth_service = AuthService(db, redis)
    await auth_service.logout(payload.refresh_token)
    return {"message": "Successfully logged out."}
