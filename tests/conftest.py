"""Фикстуры для тестов: тестовая БД и fakeredis."""

import asyncpg
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache.post import PostCache
from app.config import settings
from app.database import Base, get_session
from app.main import app
from app.redis import get_redis
from app.routers.post import get_service
from app.services.post import PostService


async def create_test_database():
    """Создаёт тестовую базу данных, если её нет."""
    dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )
    conn = await asyncpg.connect(dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", "blog_test"
        )
        if not exists:
            await conn.execute('CREATE DATABASE "blog_test"')
            print("✅ Тестовая база данных создана")
        else:
            print("✅ Тестовая база данных уже существует")
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Автоматически создаёт тестовую БД перед тестами."""
    await create_test_database()


@pytest_asyncio.fixture
async def test_engine():
    """Создаёт движок и все таблицы для тестов."""
    TEST_DATABASE_URL = (
        "postgresql+asyncpg://{user}:{password}@{host}:{port}/blog_test".format(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
        )
    )

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Сессия для тестов."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    """Фейковый Redis для тестов."""
    redis = FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_redis: FakeRedis) -> AsyncClient:
    """HTTP-клиент с подменёнными зависимостями."""

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
