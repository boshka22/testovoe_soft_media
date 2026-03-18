"""Слой кеширования: работа с постами в Redis."""

from redis.asyncio import Redis

from app.config import settings
from app.schemas.post import PostResponse


def _cache_key(post_id: int) -> str:
    return f"post:{post_id}"


class PostCache:
    """Операции кеширования постов в Redis.

    Использует паттерн Cache-Aside:
        - get: проверяет кеш, возвращает None при промахе
        - set: кладёт данные в кеш с TTL
        - delete: инвалидирует кеш при обновлении или удалении поста
    """

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def get(self, post_id: int) -> PostResponse | None:
        raw = await self._redis.get(_cache_key(post_id))
        if raw is None:
            return None
        return PostResponse.model_validate_json(raw)

    async def set(self, post: PostResponse) -> None:
        await self._redis.setex(
            name=_cache_key(post.id),
            time=settings.redis_ttl,
            value=post.model_dump_json(),
        )

    async def delete(self, post_id: int) -> None:
        await self._redis.delete(_cache_key(post_id))
