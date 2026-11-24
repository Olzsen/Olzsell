from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки экземпляра приложения из .env и переменных окружения."""

    telegram_bot_token: str
    database_url: str = "sqlite+aiosqlite:///./data/funpay_telegram.db"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_data_directory() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
