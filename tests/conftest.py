"""Фикстуры для тестов: тестовая БД и fakeredis."""

import os

import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache.post import PostCache
from app.database import Base, get_session
from app.main import app
from app.redis import get_redis
from app.routers.post import get_service
from app.services.post import PostService

TEST_DATABASE_URL = (
    "postgresql+asyncpg://{user}:{password}@{host}:{port}/blog_test".format(
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )
)


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    redis = FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_redis: FakeRedis) -> AsyncClient:
    """HTTP-клиент с подменёнными зависимостями БД и Redis."""

    def override_session():
        yield db_session

    def override_redis():
        yield fake_redis

    def override_service():
        return PostService(
            session=db_session,
            cache=PostCache(fake_redis),
        )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_service] = override_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
