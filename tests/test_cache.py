"""Интеграционные тесты логики кеширования постов."""

import pytest
from httpx import AsyncClient


async def _create_post(client: AsyncClient, **kwargs) -> dict:
    """Вспомогательная функция создания поста через API."""
    payload = {
        "title": kwargs.get("title", "Тестовый пост"),
        "content": kwargs.get("content", "Содержимое поста"),
        "author": kwargs.get("author", "Автор"),
    }
    response = await client.post("/posts", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
class TestCacheLogic:
    """Тесты паттерна Cache-Aside для GET /posts/{id}."""

    async def test_cache_miss_then_hit(self, client: AsyncClient, fake_redis) -> None:
        """Первый запрос — cache miss (идёт в БД), второй — cache hit."""
        post = await _create_post(client)
        post_id = post["id"]
        cache_key = f"post:{post_id}"

        assert await fake_redis.get(cache_key) is None

        response = await client.get(f"/posts/{post_id}")
        assert response.status_code == 200
        assert response.json()["id"] == post_id
        assert await fake_redis.get(cache_key) is not None

        response2 = await client.get(f"/posts/{post_id}")
        assert response2.status_code == 200
        assert response2.json()["id"] == post_id

    async def test_views_incremented_on_cache_miss(self, client: AsyncClient) -> None:
        """При cache miss счётчик просмотров увеличивается."""
        post = await _create_post(client)
        post_id = post["id"]
        assert post["views_count"] == 0

        response = await client.get(f"/posts/{post_id}")
        assert response.json()["views_count"] == 1

    async def test_views_incremented_on_cache_hit(
        self, client: AsyncClient, fake_redis
    ) -> None:
        """При cache hit счётчик просмотров тоже увеличивается."""
        post = await _create_post(client)
        post_id = post["id"]

        await client.get(f"/posts/{post_id}")
        assert await fake_redis.get(f"post:{post_id}") is not None

        response = await client.get(f"/posts/{post_id}")
        assert response.status_code == 200

        list_response = await client.get("/posts?skip=0&limit=10")
        post_from_list = next(
            p for p in list_response.json()["items"] if p["id"] == post_id
        )
        assert post_from_list["views_count"] == 2

    async def test_update_invalidates_cache(
        self, client: AsyncClient, fake_redis
    ) -> None:
        """PATCH инвалидирует кеш — следующий GET снова идёт в БД."""
        post = await _create_post(client, title="Старый заголовок")
        post_id = post["id"]
        cache_key = f"post:{post_id}"

        await client.get(f"/posts/{post_id}")
        assert await fake_redis.get(cache_key) is not None

        patch_response = await client.patch(
            f"/posts/{post_id}", json={"title": "Новый заголовок"}
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Новый заголовок"
        assert await fake_redis.get(cache_key) is None

        get_response = await client.get(f"/posts/{post_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Новый заголовок"
        assert await fake_redis.get(cache_key) is not None

    async def test_delete_invalidates_cache(
        self, client: AsyncClient, fake_redis
    ) -> None:
        """DELETE инвалидирует кеш — следующий GET возвращает 404."""
        post = await _create_post(client)
        post_id = post["id"]
        cache_key = f"post:{post_id}"

        await client.get(f"/posts/{post_id}")
        assert await fake_redis.get(cache_key) is not None

        delete_response = await client.delete(f"/posts/{post_id}")
        assert delete_response.status_code == 204
        assert await fake_redis.get(cache_key) is None

        get_response = await client.get(f"/posts/{post_id}")
        assert get_response.status_code == 404

    async def test_get_nonexistent_post_returns_404(self, client: AsyncClient) -> None:
        """GET несуществующего поста возвращает 404."""
        response = await client.get("/posts/99999")
        assert response.status_code == 404
        assert "detail" in response.json()


@pytest.mark.asyncio
class TestCRUD:
    """Тесты CRUD-операций и REST-контракта."""

    async def test_create_post_returns_201(self, client: AsyncClient) -> None:
        """POST создаёт пост и возвращает 201 с Location заголовком."""
        response = await client.post(
            "/posts",
            json={"title": "Новый пост", "content": "Текст", "author": "Автор"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Новый пост"
        assert data["views_count"] == 0
        assert "id" in data
        assert response.headers.get("location") == f"/posts/{data['id']}"

    async def test_list_posts_returns_pagination_meta(
        self, client: AsyncClient
    ) -> None:
        """GET /posts возвращает список с метаданными пагинации."""
        await _create_post(client)
        response = await client.get("/posts?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["items"], list)

    async def test_list_posts_respects_limit(self, client: AsyncClient) -> None:
        """GET /posts?limit=1 возвращает не более одного поста."""
        await _create_post(client, title="Пост 1")
        await _create_post(client, title="Пост 2")
        response = await client.get("/posts?skip=0&limit=1")
        assert len(response.json()["items"]) == 1

    async def test_create_post_empty_title_returns_422(
        self, client: AsyncClient
    ) -> None:
        """POST с пустым title возвращает 422."""
        response = await client.post(
            "/posts",
            json={"title": "", "content": "Текст", "author": "Автор"},
        )
        assert response.status_code == 422

    async def test_create_post_missing_field_returns_422(
        self, client: AsyncClient
    ) -> None:
        """POST без обязательного поля возвращает 422."""
        response = await client.post(
            "/posts",
            json={"title": "Заголовок", "author": "Автор"},
        )
        assert response.status_code == 422

    async def test_update_nonexistent_post_returns_404(
        self, client: AsyncClient
    ) -> None:
        """PATCH несуществующего поста возвращает 404."""
        response = await client.patch("/posts/99999", json={"title": "Новый заголовок"})
        assert response.status_code == 404

    async def test_update_partial_fields(self, client: AsyncClient) -> None:
        """PATCH обновляет только переданные поля."""
        post = await _create_post(client, title="Оригинал", author="Автор")
        response = await client.patch(f"/posts/{post['id']}", json={"title": "Изменён"})
        data = response.json()
        assert data["title"] == "Изменён"
        assert data["author"] == "Автор"  # не тронуто

    async def test_delete_nonexistent_post_returns_404(
        self, client: AsyncClient
    ) -> None:
        """DELETE несуществующего поста возвращает 404."""
        response = await client.delete("/posts/99999")
        assert response.status_code == 404

    async def test_health_check(self, client: AsyncClient) -> None:
        """GET /health возвращает 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
