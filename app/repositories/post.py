"""Модуль взаимодействия с БД в рамках таблицы posts."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.schemas.post import PostCreate, PostUpdate


class PostRepository:
    """CRUD-операции над моделью Post."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, post_id: int) -> Post | None:
        result = await self._session.execute(select(Post).where(Post.id == post_id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 20) -> tuple[list[Post], int]:
        """Возвращает страницу постов и общее количество.

        Args:
            skip: Количество пропускаемых записей.
            limit: Максимальное количество записей на странице.

        Returns:
            Кортеж (список постов, общее количество).
        """
        posts_result = await self._session.execute(
            select(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit)
        )
        count_result = await self._session.execute(select(func.count(Post.id)))
        return list(posts_result.scalars().all()), count_result.scalar_one()

    async def create(self, data: PostCreate) -> Post:
        """Создаёт новый пост и возвращает его."""
        post = Post(**data.model_dump())
        self._session.add(post)
        await self._session.commit()
        await self._session.refresh(post)
        return post

    async def update(self, post: Post, data: PostUpdate) -> Post:
        """Частично обновляет пост и возвращает обновлённую версию."""
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(post, field, value)
        await self._session.commit()
        await self._session.refresh(post)
        return post

    async def delete(self, post: Post) -> None:
        await self._session.delete(post)
        await self._session.commit()

    async def increment_views(self, post: Post) -> None:
        """Увеличивает счётчик просмотров и обновляет объект в памяти."""
        post.views_count += 1
        await self._session.commit()
        await self._session.refresh(post)

    async def increment_views_by_id(self, post_id: int) -> None:
        """Увеличивает счётчик просмотров по ID без загрузки объекта.

        Используется при cache hit, когда ORM-объект не загружен в сессию.
        """
        await self._session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(views_count=Post.views_count + 1)
        )
        await self._session.commit()

    async def refresh(self, post: Post) -> None:
        await self._session.refresh(post)
