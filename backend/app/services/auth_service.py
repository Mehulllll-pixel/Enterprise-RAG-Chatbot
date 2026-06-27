import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.models.user import User
from app.schemas.user import LoginRequest, Token
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import AuthenticationException
from app.utils.logger import logger

class AuthService:
    """Service handling access control operations, token generations, and security logic."""
    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, credentials: LoginRequest) -> User:
        """Authenticate user credentials and return User if valid."""
        user = await self.user_repo.get_by_email(credentials.email)
        if not user:
            logger.warning(f"Failed login attempt: email '{credentials.email}' not found.")
            raise AuthenticationException("Incorrect email or password.")

        if not user.is_active:
            logger.warning(f"Failed login attempt: account '{credentials.email}' is deactivated.")
            raise AuthenticationException("User account is inactive. Please contact your administrator.")

        if not verify_password(credentials.password, user.hashed_password):
            logger.warning(f"Failed login attempt: invalid password for email '{credentials.email}'.")
            raise AuthenticationException("Incorrect email or password.")

        return user

    async def login(self, credentials: LoginRequest) -> Token:
        """Process login request and yield access/refresh tokens."""
        user = await self.authenticate_user(credentials)
        
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def refresh_session(self, refresh_token: str) -> Dict[str, str]:
        """Validate refresh token and issue a new access token."""
        # Check if refresh token is in blocklist
        is_blocked = await self.redis.get(f"blocklist:{refresh_token}")
        if is_blocked:
            raise AuthenticationException("Session has been terminated or logged out.")

        try:
            payload = decode_token(refresh_token, is_refresh=True)
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise AuthenticationException("Token missing subject identifiers.")
        except Exception:
            raise AuthenticationException("Invalid or expired session token.")

        user_uuid = uuid.UUID(user_id_str)
        user = await self.user_repo.get(user_uuid)
        if not user or not user.is_active:
            raise AuthenticationException("User session is invalid or deactivated.")

        # Re-issue access token
        new_access_token = create_access_token(subject=user.id)
        return {"access_token": new_access_token, "token_type": "bearer"}

    async def logout(self, refresh_token: str) -> None:
        """Blocklist refresh token to terminate session."""
        try:
            payload = decode_token(refresh_token, is_refresh=True)
            exp = payload.get("exp")
            if exp:
                # Calculate time left for the token to expire
                import time
                remaining_ttl = int(exp - time.time())
                if remaining_ttl > 0:
                    # Store in Redis with TTL so it auto expires when no longer valid
                    await self.redis.setex(f"blocklist:{refresh_token}", remaining_ttl, "logged_out")
        except Exception:
            # If the token is invalid, it is already useless, so do nothing
            pass
        logger.info("Successfully terminated user session and blocklisted refresh token.")
