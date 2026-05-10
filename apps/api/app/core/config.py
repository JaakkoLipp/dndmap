from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(
        default="D&D Campaign Map API",
        validation_alias=AliasChoices("DND_MAP_APP_NAME", "APP_NAME"),
    )
    version: str = Field(
        default="0.1.0",
        validation_alias=AliasChoices("DND_MAP_VERSION", "APP_VERSION"),
    )
    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("DND_MAP_ENVIRONMENT", "APP_ENV", "ENVIRONMENT"),
    )
    api_prefix: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("DND_MAP_API_PREFIX", "API_PREFIX"),
    )
    enable_cors: bool = Field(
        default=True,
        validation_alias=AliasChoices("DND_MAP_ENABLE_CORS", "ENABLE_CORS"),
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        validation_alias=AliasChoices(
            "DND_MAP_CORS_ORIGINS",
            "CORS_ORIGINS",
            "CSRF_TRUSTED_ORIGINS",
        ),
    )
    persistence_backend: Literal["memory"] = Field(
        default="memory",
        validation_alias=AliasChoices(
            "DND_MAP_PERSISTENCE_BACKEND",
            "PERSISTENCE_BACKEND",
        ),
    )
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_REDIS_URL", "REDIS_URL"),
    )
    s3_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_S3_BUCKET", "S3_BUCKET"),
    )
    s3_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("DND_MAP_S3_REGION", "S3_REGION"),
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_S3_ENDPOINT_URL", "S3_ENDPOINT_URL"),
    )
    s3_public_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_S3_PUBLIC_ENDPOINT_URL",
            "S3_PUBLIC_ENDPOINT_URL",
        ),
    )
    s3_access_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_S3_ACCESS_KEY_ID", "S3_ACCESS_KEY_ID"),
    )
    s3_secret_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_S3_SECRET_ACCESS_KEY",
            "S3_SECRET_ACCESS_KEY",
        ),
    )
    s3_force_path_style: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "DND_MAP_S3_FORCE_PATH_STYLE",
            "S3_FORCE_PATH_STYLE",
        ),
    )
    session_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_SESSION_SECRET", "SESSION_SECRET"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
