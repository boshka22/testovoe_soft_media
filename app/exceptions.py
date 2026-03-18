"""Кастомные исключения и их HTTP-обработчики."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class PostNotFoundError(Exception):
    """Пост с указанным ID не найден."""

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id
        super().__init__(f"Post with id={post_id} not found.")


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений в приложении FastAPI."""

    @app.exception_handler(PostNotFoundError)
    async def post_not_found_handler(
        request: Request, exc: PostNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Перехватывает все необработанные исключения.

        Логирует полный traceback и возвращает клиенту обезличенный 500,
        не раскрывая внутренние детали реализации.
        """
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )
