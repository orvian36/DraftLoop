"""Centralized Pydantic Settings for DraftLoop.

Single source of truth for runtime config. Use ``get_settings()`` everywhere.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from draftloop_core.errors import ConfigError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gemini_api_key: SecretStr = Field(...)
    drafter_model: str = Field(default="gemini-2.5-pro")
    drafter_mode: Literal["single_call", "two_call"] = "single_call"
    extraction_model: str = Field(default="gemini-2.5-flash")
    embed_model: str = Field(default="gemini-embedding-001")
    embed_dim: int = Field(default=1536, ge=128, le=3072)
    reranker: Literal["flash", "bge"] = "flash"

    critic_enabled: bool = True
    critic_auto_apply: bool = False
    seed_on_boot: bool = True
    eval_cost_budget_usd: float = 2.0

    store: Literal["sqlite", "postgres"] = "sqlite"
    vector_store: Literal["chroma", "qdrant"] = "chroma"
    blob_store: Literal["local", "s3"] = "local"
    data_dir: str = "./data"

    langfuse_host: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    port_api: int = 8000
    port_web: int = 3000

    def __init__(self, **kwargs: Any) -> None:
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            raise ConfigError(
                f"invalid settings: {e}",
                code="CONFIG_VALIDATION",
            ) from e


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
