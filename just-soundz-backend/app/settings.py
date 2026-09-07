from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_ALLOWED_ORIGIN = "https://just-soundz-ai-companion.justmarsh88.chatgpt.site"


class AppSettings(BaseSettings):
    """Typed boundary for application-critical Just Maker configuration."""

    model_config = SettingsConfigDict(
        populate_by_name=True,
        case_sensitive=True,
        extra="ignore",
    )

    environment: str = Field(
        default="development",
        validation_alias="JUST_MAKER_ENVIRONMENT",
    )
    database_url: str | None = Field(
        default=None,
        validation_alias="JUST_MAKER_DATABASE_URL",
    )
    allowed_origins_raw: str = Field(
        default=DEFAULT_ALLOWED_ORIGIN,
        validation_alias="JUST_SOUNDZ_ALLOWED_ORIGINS",
    )
    require_external_generator: bool = Field(
        default=False,
        validation_alias="JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR",
    )
    primary_worker_url: str | None = Field(
        default=None,
        validation_alias="JUST_SOUNDZ_PRIMARY_WORKER_URL",
    )
    musicgen_worker_url: str | None = Field(
        default=None,
        validation_alias="JUST_SOUNDZ_MUSICGEN_WORKER_URL",
    )
    stable_worker_url: str | None = Field(
        default=None,
        validation_alias="JUST_SOUNDZ_STABLE_WORKER_URL",
    )

    @property
    def allowed_origins(self) -> list[str]:
        origins = [
            value.strip()
            for value in self.allowed_origins_raw.split(",")
            if value.strip()
        ]
        return origins or [DEFAULT_ALLOWED_ORIGIN]

    @property
    def external_worker_urls(self) -> list[str]:
        return [
            value
            for value in (
                self.primary_worker_url,
                self.musicgen_worker_url,
                self.stable_worker_url,
            )
            if value
        ]


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()


def validate_startup(settings: AppSettings) -> dict[str, Any]:
    """Classify startup configuration without exposing secrets.

    Development/test environments remain bootable when optional external
    infrastructure is absent. Production may require an external generator
    explicitly through JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR.
    """

    fatal: list[str] = []
    degraded: list[str] = []

    environment = settings.environment.strip().lower()
    has_external_worker = bool(settings.external_worker_urls)

    if not has_external_worker:
        if environment == "production" and settings.require_external_generator:
            fatal.append("external_generation_worker")
        else:
            degraded.append("external_generation_worker")

    if not settings.database_url:
        degraded.append("database")

    return {
        "valid": not fatal,
        "environment": environment,
        "fatal": fatal,
        "degraded": degraded,
    }
