from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    cors_origins: str = "http://localhost:3000"
    default_timezone: str = "Asia/Riyadh"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
