"""HTTP-роутер для CRUD-операций над постами."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.post import PostCache
from app.database import get_session
from app.redis import get_redis
from app.schemas.post import PostCreate, PostListResponse, PostResponse, PostUpdate
from app.services.post import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


def get_service(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg] # noqa: B008
) -> PostService:
    """FastAPI dependency: собирает PostService с нужными зависимостями."""
    return PostService(session=session, cache=PostCache(redis))


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    response: Response,
    service: PostService = Depends(get_service),  # noqa: B008
) -> PostResponse:
    """Создать новый пост."""
    post = await service.create_post(data)
    response.headers["Location"] = f"/posts/{post.id}"
    return post


@router.get("", response_model=PostListResponse)
async def list_posts(
    skip: int = Query(default=0, ge=0),  # noqa: B008
    limit: int = Query(default=20, ge=1, le=100),  # noqa: B008
    service: PostService = Depends(get_service),  # noqa: B008
) -> PostListResponse:
    """Получить список постов с пагинацией."""
    return await service.list_posts(skip=skip, limit=limit)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    service: PostService = Depends(get_service),  # noqa: B008
) -> PostResponse:
    """Получить пост по ID. Использует Redis-кеш."""
    return await service.get_post(post_id)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    data: PostUpdate,
    service: PostService = Depends(get_service),  # noqa: B008
) -> PostResponse:
    """Частично обновить пост. Инвалидирует кеш."""
    return await service.update_post(post_id, data)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    service: PostService = Depends(get_service),  # noqa: B008
) -> None:
    """Удалить пост. Инвалидирует кеш."""
    await service.delete_post(post_id)
