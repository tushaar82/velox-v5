"""Redis client for caching and pub/sub."""
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from src.core.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client wrapper."""

    def __init__(self) -> None:
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info("redis_connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("redis_disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not self.redis:
            return False
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            return False

    async def publish(self, channel: str, message: Any) -> bool:
        """Publish message to channel."""
        if not self.redis:
            return False
        try:
            serialized = json.dumps(message)
            await self.redis.publish(channel, serialized)
            return True
        except Exception as e:
            logger.error("redis_publish_failed", channel=channel, error=str(e))
            return False

    async def subscribe(self, channel: str):
        """Subscribe to channel."""
        if not self.redis:
            return None
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error("redis_subscribe_failed", channel=channel, error=str(e))
            return None


# Global Redis client instance
redis_client = RedisClient()
