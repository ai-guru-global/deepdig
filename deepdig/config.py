"""Environment & timeout configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API keys read with their well-known vendor names (no prefix required).
    dashscope_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "DEEPDIG_DASHSCOPE_API_KEY"),
    )
    zhipu_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ZHIPU_API_KEY", "DEEPDIG_ZHIPU_API_KEY"),
    )
    moonshot_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MOONSHOT_API_KEY", "DEEPDIG_MOONSHOT_API_KEY"),
    )

    timeout: float = 8.0
    qwen_model: str = "qwen-plus"
    glm_model: str = "glm-4-flash"
    kimi_model: str = "kimi-latest"

    max_content_chars: int = 2000
    cache_ttl: int = 300
    max_concurrency: int = 4

    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    access_token: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="DEEPDIG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
