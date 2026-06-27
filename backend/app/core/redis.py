import redis.asyncio as aioredis
from typing import Optional, Any
import time
from app.core.config import settings
from app.utils.logger import logger

class InMemoryRedisFallback:
    """Fallback database simulating basic Redis operations in-memory."""
    def __init__(self):
        self.store = {}
        logger.warning("InMemoryRedisFallback initialized. Session caching and blocklists will run in local RAM.")

    async def get(self, key: str) -> Optional[str]:
        val = self.store.get(key)
        if val:
            expiry, actual_val = val
            if expiry and time.time() > expiry:
                del self.store[key]
                return None
            return actual_val
        return None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expiry = (time.time() + ex) if ex else None
        self.store[key] = (expiry, str(value))

    async def setex(self, key: str, time_seconds: int, value: str) -> None:
        await self.set(key, value, ex=time_seconds)

    async def delete(self, key: str) -> None:
        if key in self.store:
            del self.store[key]

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self.store.clear()

class RedisClient:
    """Async Redis Client manager with automatic in-memory fallback."""
    def __init__(self):
        self.client: Optional[Any] = None
        self.is_fallback: bool = False

    def connect(self) -> Any:
        """Establish connection pool, or fallback to memory if Redis is unavailable."""
        if self.client:
            return self.client

        try:
            logger.info(f"Attempting connection to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            # We initialize standard client
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Run a test ping in a separate sync wrapper or schedule check
            self.client = client
            self.is_fallback = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}. Falling back to in-memory store.")
            self.client = InMemoryRedisFallback()
            self.is_fallback = True

        return self.client

    async def check_connection(self) -> None:
        """Test the connection and verify if we need to fallback."""
        if not self.client or self.is_fallback:
            return
            
        try:
            # Try to ping the real redis
            await self.client.ping()
            logger.info("Successfully connected to Redis instance.")
        except Exception as e:
            logger.warning(f"Redis ping failed: {str(e)}. Switching to in-memory fallback client.")
            await self.client.close()
            self.client = InMemoryRedisFallback()
            self.is_fallback = True

    async def close(self) -> None:
        """Close connection pools."""
        if self.client:
            logger.info("Closing Redis/Fallback client...")
            await self.client.close()
            self.client = None

# Global Redis manager instance
redis_client_manager = RedisClient()

async def get_redis() -> Any:
    """Dependency provider yielding the active Redis/Fallback client."""
    client = redis_client_manager.connect()
    # Perform quick connection test if it's a new connection
    if not redis_client_manager.is_fallback:
        await redis_client_manager.check_connection()
    return redis_client_manager.client
