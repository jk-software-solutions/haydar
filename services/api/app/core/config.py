from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "HADIR"
    api_v1_prefix: str = "/api/v1"
    database_url: str | None = None
    test_database_url: str | None = None
    migration_database_url: str | None = None
    jwt_secret: str = "development-only-change-me"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 30
    cors_origins: str = "http://localhost:3000"
    default_timezone: str = "Asia/Riyadh"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
