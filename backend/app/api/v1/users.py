import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, has_permissions
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserResponseWithRelations
from app.services.user_service import UserService
from app.models.user import User
from app.core.exceptions import AuthorizationException

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponseWithRelations, status_code=status.HTTP_200_OK)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Fetch active logged-in user profile details."""
    return current_user

@router.get(
    "",
    response_model=List[UserResponseWithRelations],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["users:read"]))]
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve list of users (Admin-only)."""
    user_service = UserService(db)
    return await user_service.list_users(skip, limit)

@router.post(
    "",
    response_model=UserResponseWithRelations,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permissions(["users:write"]))]
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user profile (Admin-only)."""
    user_service = UserService(db)
    return await user_service.create_user(user_in)

@router.get(
    "/{id}",
    response_model=UserResponseWithRelations,
    status_code=status.HTTP_200_OK
)
async def get_user_profile(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch profile of a specific user. Restricts to self or Admins."""
    if current_user.id != id and "users:read" not in current_user.role.permissions:
        raise AuthorizationException("You do not have permission to view other users' profiles.")
    
    user_service = UserService(db)
    return await user_service.get_user_by_id(id)

@router.put(
    "/{id}",
    response_model=UserResponseWithRelations,
    status_code=status.HTTP_200_OK
)
async def update_user_profile(
    id: uuid.UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update profile parameters. Restricts to self or Admins with write permissions."""
    if current_user.id != id and "users:write" not in current_user.role.permissions:
        raise AuthorizationException("You do not have permission to update other users' profiles.")
        
    # Prevent non-admin users from changing their own roles or departments
    if "users:write" not in current_user.role.permissions:
        user_update.role_id = None
        user_update.department_id = None
        user_update.is_active = None

    user_service = UserService(db)
    return await user_service.update_user(id, user_update)

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["users:write"]))]
)
async def delete_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a user profile (Admin-only)."""
    user_service = UserService(db)
    await user_service.delete_user(id)
    return {"message": "User deleted successfully."}
