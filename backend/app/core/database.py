from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.utils.logger import logger

# Configure connection pooling to support high concurrency
# pool_size: The number of connections to keep open in the pool.
# max_overflow: The number of connections to allow past the pool_size.
# Check if database is SQLite and adjust arguments accordingly
is_sqlite = settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # SQLite does not support pool_size or max_overflow
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
else:
    # PostgreSQL pool settings for high concurrency
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yield provider for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error occurred: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()
