"""Настройки приложения из переменных окружения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения.

    Все значения читаются из переменных окружения или .env файла.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "blog"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_ttl: int = 300  # секунды

    # App
    debug: bool = False

    @property
    def database_url(self) -> str:
        """Асинхронный DSN для SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
