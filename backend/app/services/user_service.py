import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository, RoleRepository, DepartmentRepository
from app.core.security import hash_password
from app.core.exceptions import ConflictException, EntityNotFoundException, ValidationException

class UserService:
    """Business service layer for user management operations."""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.dept_repo = DepartmentRepository(db)

    async def create_user(self, user_in: UserCreate) -> User:
        """Register a new user inside the organization after validating credentials."""
        # 1. Check duplicate email
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictException(f"User with email '{user_in.email}' already exists.")

        # 2. Check role validity
        role = await self.role_repo.get_role_by_id(user_in.role_id)
        if not role:
            raise ValidationException(f"Specified role '{user_in.role_id}' is invalid.")

        # 3. Check department validity
        if user_in.department_id:
            dept = await self.dept_repo.get(user_in.department_id)
            if not dept:
                raise ValidationException("Specified department ID does not exist.")

        # 4. Hash password and build object
        hashed_pwd = hash_password(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
            role_id=user_in.role_id,
            department_id=user_in.department_id,
            is_active=user_in.is_active
        )
        
        created = await self.user_repo.create(db_user)
        await self.db.commit()
        # Fetch with relationships loaded
        return await self.user_repo.get_with_relations(created.id)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Retrieve user profile, raising 404 if not found."""
        user = await self.user_repo.get_with_relations(user_id)
        if not user:
            raise EntityNotFoundException(f"User with ID '{user_id}' does not exist.")
        return user

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Fetch list of users."""
        return await self.user_repo.list_with_relations(skip, limit)

    async def update_user(self, user_id: uuid.UUID, user_update: UserUpdate) -> User:
        """Update active profile parameters."""
        user = await self.get_user_by_id(user_id)
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.user_repo.get_by_email(update_data["email"])
            if existing:
                raise ConflictException("Email is already registered by another user.")
                
        if "role_id" in update_data:
            role = await self.role_repo.get_role_by_id(update_data["role_id"])
            if not role:
                raise ValidationException("Specified role is invalid.")
                
        if "department_id" in update_data and update_data["department_id"]:
            dept = await self.dept_repo.get(update_data["department_id"])
            if not dept:
                raise ValidationException("Specified department is invalid.")

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data["password"])
            del update_data["password"]

        await self.user_repo.update(user, update_data)
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Purge a user from records."""
        user = await self.get_user_by_id(user_id)
        await self.user_repo.delete(user.id)
        await self.db.commit()
