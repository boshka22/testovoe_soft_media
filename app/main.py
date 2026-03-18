"""Точка входа FastAPI-приложения."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.exceptions import register_exception_handlers
from app.routers.post import router as posts_router

app = FastAPI(
    title="Blog API",
    description="REST API для блога с Redis-кешированием популярных постов.",
    version="1.0.0",
)

register_exception_handlers(app)
app.include_router(posts_router)


@app.get("/health", tags=["health"], include_in_schema=False)
async def health_check() -> JSONResponse:
    """Проверка работоспособности сервиса."""
    return JSONResponse(content={"status": "ok"})
