"""Pydantic-схемы для постов."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_serializers import field_serializer


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=100)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1, max_length=100)


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    author: str
    views_count: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime) -> str:
        """Конвертирует naive datetime в ISO строку с UTC timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    skip: int
    limit: int
