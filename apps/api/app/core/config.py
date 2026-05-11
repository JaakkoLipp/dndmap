import json
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource


class _CommaListEnvSource(EnvSettingsSource):
    """Accepts comma-separated strings for list fields in addition to JSON arrays."""

    def decode_complex_value(self, field_name: str, field, value: str) -> object:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return [item.strip() for item in value.split(",") if item.strip()]


class _CommaListDotenvSource(DotEnvSettingsSource):
    def decode_complex_value(self, field_name: str, field, value: str) -> object:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _CommaListEnvSource(settings_cls),
            _CommaListDotenvSource(settings_cls),
            file_secret_settings,
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
    persistence_backend: Literal["memory", "postgres"] = Field(
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
    rate_limit_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DND_MAP_RATE_LIMIT_ENABLED",
            "RATE_LIMIT_ENABLED",
        ),
    )
    auth_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("DND_MAP_AUTH_ENABLED", "AUTH_ENABLED"),
    )
    local_login_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DND_MAP_LOCAL_LOGIN_ENABLED",
            "LOCAL_LOGIN_ENABLED",
        ),
    )
    jwt_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DND_MAP_JWT_SECRET", "JWT_SECRET"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("DND_MAP_JWT_ALGORITHM", "JWT_ALGORITHM"),
    )
    jwt_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias=AliasChoices("DND_MAP_JWT_EXPIRE_MINUTES", "JWT_EXPIRE_MINUTES"),
    )
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8080/api/v1/auth",
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_REDIRECT_BASE_URL",
            "OAUTH_REDIRECT_BASE_URL",
        ),
    )
    oauth_discord_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_DISCORD_CLIENT_ID",
            "OAUTH_DISCORD_CLIENT_ID",
        ),
    )
    oauth_discord_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_DISCORD_CLIENT_SECRET",
            "OAUTH_DISCORD_CLIENT_SECRET",
        ),
    )
    oauth_google_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_GOOGLE_CLIENT_ID",
            "OAUTH_GOOGLE_CLIENT_ID",
        ),
    )
    oauth_google_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_GOOGLE_CLIENT_SECRET",
            "OAUTH_GOOGLE_CLIENT_SECRET",
        ),
    )
    oauth_github_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_GITHUB_CLIENT_ID",
            "OAUTH_GITHUB_CLIENT_ID",
        ),
    )
    oauth_github_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DND_MAP_OAUTH_GITHUB_CLIENT_SECRET",
            "OAUTH_GITHUB_CLIENT_SECRET",
        ),
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
