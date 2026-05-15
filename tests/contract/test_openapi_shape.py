"""Contract: OpenAPI schema must include /health and /version, and the
metadata must be stable so the generated TS client doesn't churn.
"""

import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    from draftloop_core.config import get_settings
    get_settings.cache_clear()
    return TestClient(create_app())


def test_openapi_lists_health_and_version(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = schema["paths"]
    assert "/health" in paths
    assert "/version" in paths


def test_openapi_has_app_metadata(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "DraftLoop API"
    assert schema["info"]["version"].count(".") == 2
