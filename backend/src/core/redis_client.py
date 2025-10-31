"""
Redis client for caching and session management.
Provides connection pooling and common cache operations.
"""
import json
from typing import Optional, Any
from datetime import timedelta
import redis.asyncio as redis
from .config import get_settings


settings = get_settings()


class RedisClient:
    """Redis client wrapper with caching utilities."""

    def __init__(self, url: Optional[str] = None) -> None:
        """
        Initialize Redis client.

        Args:
            url: Redis connection URL (uses settings if not provided)
        """
        self.url = url or settings.REDIS_URL
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        self.client = await redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.set(key, value, ex=expire)

    async def get_json(self, key: str) -> Optional[Any]:
        """
        Get JSON value from cache.

        Args:
            key: Cache key

        Returns:
            Deserialized JSON value or None
        """
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set JSON value in cache.

        Args:
            key: Cache key
            value: Value to serialize and cache
            expire: Expiration time in seconds

        Returns:
            True if successful
        """
        json_value = json.dumps(value)
        return await self.set(key, json_value, expire)

    async def delete(self, key: str) -> int:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            Number of keys deleted
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.expire(key, seconds)

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.

        Args:
            key: Cache key
            amount: Increment amount

        Returns:
            New value
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.incrby(key, amount)

    async def get_pattern(self, pattern: str) -> list[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            List of matching keys
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.keys(pattern)

    async def flush_db(self) -> bool:
        """
        Flush all keys from current database.

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.flushdb()


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Dependency for getting Redis client.

    Returns:
        Redis client instance
    """
    if not redis_client.client:
        await redis_client.connect()
    return redis_client


# Cache key generators
def get_user_cache_key(user_id: int) -> str:
    """Generate cache key for user data."""
    return f"user:{user_id}"


def get_strategy_cache_key(strategy_id: int) -> str:
    """Generate cache key for strategy data."""
    return f"strategy:{strategy_id}"


def get_market_data_cache_key(symbol: str) -> str:
    """Generate cache key for market data."""
    return f"market_data:{symbol}"


def get_position_cache_key(strategy_id: int) -> str:
    """Generate cache key for positions."""
    return f"positions:{strategy_id}"
