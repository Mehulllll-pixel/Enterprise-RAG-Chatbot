import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, engine
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.department import Department
from app.utils.logger import logger

# Default role permissions mapping
DEFAULT_ROLES = [
    {
        "id": "ADMIN",
        "description": "System Administrator - full system access",
        "permissions": [
            "users:read", "users:write",
            "doc:upload", "doc:read", "doc:write",
            "chat:read", "chat:write",
            "analytics:read", "settings:write"
        ]
    },
    {
        "id": "MANAGER",
        "description": "Department Manager - upload and manage departmental documents",
        "permissions": [
            "doc:upload", "doc:read", "doc:write",
            "chat:read", "chat:write",
            "analytics:read"
        ]
    },
    {
        "id": "ENGINEER",
        "description": "Engineer - upload documents and interact with chatbot",
        "permissions": [
            "doc:upload", "doc:read",
            "chat:read", "chat:write"
        ]
    },
    {
        "id": "OPERATOR",
        "description": "Operator - interact with chatbot only",
        "permissions": [
            "chat:read", "chat:write"
        ]
    },
    {
        "id": "VIEWER",
        "description": "Viewer - read-only access to documents and public chats",
        "permissions": [
            "doc:read", "chat:read"
        ]
    }
]

async def seed_database(db: AsyncSession) -> None:
    """Seed roles, department, and default admin user into database."""
    logger.info("Starting database seeding...")

    # 1. Seed Roles
    for role_data in DEFAULT_ROLES:
        query = select(Role).where(Role.id == role_data["id"])
        result = await db.execute(query)
        db_role = result.scalar_one_or_none()

        if not db_role:
            logger.info(f"Seeding Role: {role_data['id']}")
            role = Role(
                id=role_data["id"],
                description=role_data["description"],
                permissions=role_data["permissions"]
            )
            db.add(role)
        else:
            logger.info(f"Role {role_data['id']} already exists. Updating permissions.")
            db_role.permissions = role_data["permissions"]
            db_role.description = role_data["description"]
            db.add(db_role)

    await db.flush()

    # 2. Seed Default Department
    query = select(Department).where(Department.code == settings.INITIAL_ADMIN_DEPARTMENT_CODE)
    result = await db.execute(query)
    db_dept = result.scalar_one_or_none()

    if not db_dept:
        logger.info(f"Seeding default department: {settings.INITIAL_ADMIN_DEPARTMENT}")
        db_dept = Department(
            name=settings.INITIAL_ADMIN_DEPARTMENT,
            code=settings.INITIAL_ADMIN_DEPARTMENT_CODE
        )
        db.add(db_dept)
        await db.flush()
    else:
        logger.info(f"Department {settings.INITIAL_ADMIN_DEPARTMENT_CODE} already exists.")

    # 3. Seed Admin User
    query = select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL)
    result = await db.execute(query)
    db_admin = result.scalar_one_or_none()

    if not db_admin:
        logger.info(f"Seeding admin user: {settings.INITIAL_ADMIN_EMAIL}")
        admin_pwd = hash_password(settings.INITIAL_ADMIN_PASSWORD)
        admin = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            hashed_password=admin_pwd,
            full_name=settings.INITIAL_ADMIN_FULL_NAME,
            role_id="ADMIN",
            department_id=db_dept.id,
            is_active=True
        )
        db.add(admin)
    else:
        logger.info(f"Admin user {settings.INITIAL_ADMIN_EMAIL} already exists.")

    await db.commit()
    logger.info("Database seeding successfully completed.")

async def main():
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
