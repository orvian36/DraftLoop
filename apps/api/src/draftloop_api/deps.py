"""FastAPI dependency providers (DI surface)."""

from __future__ import annotations

from draftloop_core.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()
