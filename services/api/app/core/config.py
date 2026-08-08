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
    platform_admin_emails: str = ""
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10000)
    auth_rate_limit_per_minute: int = Field(default=20, ge=5, le=1000)
    password_reset_token_minutes: int = Field(default=30, ge=5, le=120)
    password_reset_url_base: str = "http://localhost:3000/en/reset-password"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_starttls: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def platform_admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.platform_admin_emails.split(",")
            if email.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
