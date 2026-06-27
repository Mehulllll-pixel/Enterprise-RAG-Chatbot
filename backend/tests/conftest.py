import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.base import Base
from app.models.user import User, Role
from app.models.department import Department
from app.core.security import hash_password
from app.utils.seeder import DEFAULT_ROLES

# Test Database Configuration - In-memory SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Mock Redis Client
class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        self.store[key] = str(value)

    async def setex(self, key: str, time_seconds: int, value: str):
        self.store[key] = str(value)

    async def delete(self, key: str):
        self.store.pop(key, None)

    async def ping(self):
        return True

    async def close(self):
        self.store.clear()

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create session scoped event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Database fixture recreating tables for every test function."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        # Seed basic roles for tests
        for role_data in DEFAULT_ROLES:
            role = Role(
                id=role_data["id"],
                description=role_data["description"],
                permissions=role_data["permissions"]
            )
            session.add(role)
        
        # Seed test department
        dept = Department(name="Engineering", code="ENG")
        session.add(dept)
        await session.flush()
        
        # Seed test admin
        admin = User(
            email="admin@test.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Test Admin",
            role_id="ADMIN",
            department_id=dept.id
        )
        session.add(admin)
        await session.commit()
        
    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client mocking database and Redis dependencies."""
    mock_redis = MockRedis()

    async def override_get_db():
        yield db

    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # FastAPI 0.110+ uses ASGITransport for AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
