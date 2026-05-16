"""Smoke: API can boot in-process and serve /health and /version.

Web smoke (Playwright) lands in Plan 4 once there's a real editor.
"""

from __future__ import annotations

import pytest
from draftloop_api.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    from draftloop_core.config import get_settings

    get_settings.cache_clear()
    return TestClient(create_app())


def test_health_and_version_are_consistent(client):
    h = client.get("/health").json()
    v = client.get("/version").json()
    assert h["status"] == "ok"
    assert v["version"] == "0.1.0"
