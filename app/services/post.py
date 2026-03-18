"""Сервисный слой: бизнес-логика операций с постами."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.post import PostCache
from app.exceptions import PostNotFoundError
from app.repositories.post import PostRepository
from app.schemas.post import PostCreate, PostListResponse, PostResponse, PostUpdate


class PostService:
    """Оркестрирует операции над постами между БД и кешем.

    Реализует паттерн Cache-Aside:
        - чтение: кеш → БД → кеш
        - запись/удаление: БД → инвалидация кеша

    Замечание по race condition:
        При конкурентных cache miss несколько запросов могут одновременно
        обратиться к БД. Для продакшена решается через
        Redis SET NX lock на время первого запроса. В рамках данного задания
        не реализовано.
    """

    def __init__(self, session: AsyncSession, cache: PostCache) -> None:
        self._repo = PostRepository(session)
        self._cache = cache

    async def get_post(self, post_id: int) -> PostResponse:
        """Возвращает пост по ID с кешированием.

        Счётчик просмотров увеличивается при каждом вызове — как при
        cache miss (через ORM-объект), так и при cache hit (через UPDATE по ID).

        Args:
            post_id: ID запрашиваемого поста.

        Returns:
            PostResponse с данными поста.

        Raises:
            PostNotFoundError: Пост не найден в БД.
        """
        cached = await self._cache.get(post_id)

        if cached is None:
            post = await self._repo.get_by_id(post_id)
            if post is None:
                raise PostNotFoundError(post_id)
            await self._repo.increment_views(post)
            cached = PostResponse.model_validate(post)
            await self._cache.set(cached)
        else:
            await self._repo.increment_views_by_id(post_id)

        return cached

    async def list_posts(self, skip: int, limit: int) -> PostListResponse:
        """Возвращает список постов с пагинацией (без кеширования).

        Args:
            skip: Количество пропускаемых записей.
            limit: Максимальное количество записей на странице.
        """
        posts, total = await self._repo.get_all(skip=skip, limit=limit)
        return PostListResponse(
            items=[PostResponse.model_validate(p) for p in posts],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create_post(self, data: PostCreate) -> PostResponse:
        """Создаёт новый пост.

        Args:
            data: Данные для создания поста.
        """
        post = await self._repo.create(data)
        return PostResponse.model_validate(post)

    async def update_post(self, post_id: int, data: PostUpdate) -> PostResponse:
        """Обновляет пост и инвалидирует его кеш.

        Args:
            post_id: ID обновляемого поста.
            data: Поля для обновления (только переданные).

        Raises:
            PostNotFoundError: Пост не найден.
        """
        post = await self._repo.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError(post_id)

        updated = await self._repo.update(post, data)
        await self._cache.delete(post_id)
        return PostResponse.model_validate(updated)

    async def delete_post(self, post_id: int) -> None:
        """Удаляет пост и инвалидирует его кеш.

        Args:
            post_id: ID удаляемого поста.

        Raises:
            PostNotFoundError: Пост не найден.
        """
        post = await self._repo.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError(post_id)

        await self._repo.delete(post)
        await self._cache.delete(post_id)
