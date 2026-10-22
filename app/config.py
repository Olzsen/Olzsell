from pathlib import Path
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")
    telegram_bot_token: SecretStr = Field(default=SecretStr(""))
    admin_telegram_id: int
    api_key: SecretStr
    database_url: str = "sqlite+aiosqlite:///./data/olzsell.db"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    max_plugin_upload_mb: int = Field(default=1, ge=1, le=10)
    playerok_token: SecretStr | None = None
    playerok_user_agent: str = ""
    playerok_extra_cookies_json: SecretStr | None = None
    playerok_mode: str = "demo"

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) < 32 or raw.lower().startswith("replace-with"):
            raise ValueError("API_KEY must be a random secret with at least 32 characters")
        return value

    @field_validator("telegram_bot_token")
    @classmethod
    def validate_telegram_token(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        return value

    @property
    def data_dir(self) -> Path:
        return ROOT_DIR / "data"

    @property
    def plugins_dir(self) -> Path:
        return ROOT_DIR / "plugins"
