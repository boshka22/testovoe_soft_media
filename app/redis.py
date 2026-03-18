"""Redis dependency для FastAPI."""

from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.config import settings


async def get_redis() -> AsyncGenerator[Redis, None]:  # type: ignore[type-arg]
    """FastAPI dependency: предоставляет Redis-клиент на время запроса."""
    client: Redis = Redis.from_url(  # type: ignore[type-arg]
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.close()
