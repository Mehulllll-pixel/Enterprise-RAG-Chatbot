import uuid
from typing import AsyncGenerator, Callable, List
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.core.exceptions import AuthenticationException, AuthorizationException, EntityNotFoundException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.logger import logger

# Declare OAuth2 Bearer schema
reusable_oauth2 = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token_credentials: HTTPAuthorizationCredentials = Security(reusable_oauth2)
) -> User:
    """Extract and validate access token, returning the current active user."""
    if not token_credentials:
        raise AuthenticationException("Authorization header is missing or empty.")

    token = token_credentials.credentials
    try:
        payload = decode_token(token, is_refresh=False)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationException("JWT payload is missing sub parameter.")
    except JWTError:
        raise AuthenticationException("Could not validate credentials.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException("Invalid user identifier in token.")

    user_repo = UserRepository(db)
    user = await user_repo.get_with_relations(user_uuid)
    
    if not user:
        raise EntityNotFoundException("Current logged-in user profile not found.")
    
    if not user.is_active:
        raise AuthorizationException("Your user account has been deactivated.")

    return user

class PermissionChecker:
    """Dependency factory checking if the logged user satisfies role constraints."""
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_permissions = current_user.role.permissions
        # Verify all required permissions exist inside user permissions
        for perm in self.required_permissions:
            if perm not in user_permissions:
                logger.warning(
                    f"RBAC Refusal: User {current_user.email} with role {current_user.role_id} "
                    f"lacks required permission '{perm}'."
                )
                raise AuthorizationException("Access denied. Insufficient permissions.")
        return current_user

def has_permissions(permissions: List[str]) -> Callable:
    """Syntactic decorator dependency for route parameters checking permissions."""
    return PermissionChecker(permissions)
