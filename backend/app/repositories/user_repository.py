import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models.user import User, Role
from app.models.department import Department
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository wrapping data access operations for User models."""
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email along with their department and role details."""
        query = (
            select(User)
            .where(User.email == email)
            .options(joinedload(User.role), joinedload(User.department))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_relations(self, id: uuid.UUID) -> Optional[User]:
        """Fetch user details loaded with department and role profiles."""
        query = (
            select(User)
            .where(User.id == id)
            .options(joinedload(User.role), joinedload(User.department))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_with_relations(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with active relations."""
        query = (
            select(User)
            .options(joinedload(User.role), joinedload(User.department))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

class RoleRepository(BaseRepository[Role]):
    """Repository wrapping operations for Role models."""
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        return await self.get(role_id)

class DepartmentRepository(BaseRepository[Department]):
    """Repository wrapping operations for Department models."""
    def __init__(self, db: AsyncSession):
        super().__init__(Department, db)

    async def get_by_code(self, code: str) -> Optional[Department]:
        query = select(Department).where(Department.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Department]:
        query = select(Department).where(Department.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
