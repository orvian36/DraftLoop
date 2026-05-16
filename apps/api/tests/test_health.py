import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    from draftloop_core.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] >= 0


def test_version_returns_semver(client):
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert body["version"].count(".") == 2
