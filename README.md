# Blog API

REST API для блога с Redis-кешированием популярных постов.

## Стек

| Слой        | Технология                        |
|-------------|-----------------------------------|
| Язык        | Python 3.11                       |
| Фреймворк   | FastAPI                           |
| База данных | PostgreSQL 15 + SQLAlchemy async  |
| Кеш         | Redis 7                           |
| Миграции    | Alembic                           |
| Контейнер   | Docker + docker-compose           |
| Линтеры     | black, flake8, isort, mypy        |
| Тесты       | pytest-asyncio + fakeredis        |

---

## Быстрый старт

```bash
cp .env.example .env
docker-compose up --build
```

API: **http://localhost:8000**
Swagger: **http://localhost:8000/docs**

---

## Эндпоинты

| Метод    | URL              | Описание                          |
|----------|------------------|-----------------------------------|
| `POST`   | `/posts`         | Создать пост                      |
| `GET`    | `/posts`         | Список постов (skip, limit)       |
| `GET`    | `/posts/{id}`    | Получить пост (с кешированием)    |
| `PATCH`  | `/posts/{id}`    | Обновить пост (инвалидация кеша)  |
| `DELETE` | `/posts/{id}`    | Удалить пост (инвалидация кеша)   |

---

## Логика кеширования

Реализован паттерн **Cache-Aside**:

```
GET /posts/{id}
  ├── Redis hit  → вернуть из кеша
  └── Redis miss → читать из PostgreSQL → положить в Redis (TTL=300с) → вернуть

PATCH /posts/{id}  →  обновить в PostgreSQL  →  удалить ключ из Redis
DELETE /posts/{id} →  удалить из PostgreSQL  →  удалить ключ из Redis
```

Список постов (`GET /posts`) не кешируется — инвалидация коллекций
при произвольных фильтрах и пагинации нецелесообразна.

---

## Тесты

```bash
# Запустить тесты внутри контейнера
docker-compose exec web pip install -r requirements/test.txt
docker-compose exec web pytest

# Локально (требуется PostgreSQL на localhost:5432 с БД blog_test)
pip install -r requirements/test.txt
pytest
```

---

## Линтеры

```bash
pip install -r requirements/lint.txt
pre-commit install
black .
isort .
flake8 .
mypy app/
```
