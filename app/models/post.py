"""Модуль моделей SQLAlchemy для работы с постами."""

from datetime import datetime

from sqlalchemy import BigInteger, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Post(Base):
    """Пост в блоге.

    Индексы:
        ix_posts_created_at — покрывает ORDER BY created_at DESC в list_posts,
                              избегает seq scan при пагинации.
        ix_posts_author     — покрывает фильтрацию по автору без seq scan.
    """

    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_created_at", "created_at"),
        Index("ix_posts_author", "author"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    views_count: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
