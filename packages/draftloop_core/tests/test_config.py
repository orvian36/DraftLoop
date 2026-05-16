import pytest
from draftloop_core.config import Settings, get_settings
from draftloop_core.errors import ConfigError


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DRAFTER_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("EMBED_DIM", "1536")
    s = Settings()
    assert s.gemini_api_key.get_secret_value() == "sk-test"
    assert s.drafter_model == "gemini-2.5-pro"
    assert s.embed_dim == 1536


def test_settings_defaults_applied(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    s = Settings()
    assert s.drafter_mode == "single_call"
    assert s.embed_dim == 1536
    assert s.store == "sqlite"
    assert s.vector_store == "chroma"
    assert s.blob_store == "local"


def test_settings_validates_drafter_mode(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DRAFTER_MODE", "invalid_mode")
    with pytest.raises(ConfigError):
        Settings()


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
