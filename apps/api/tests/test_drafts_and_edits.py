import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from draftloop_core.config import get_settings

    get_settings.cache_clear()
    import draftloop_api.routes.drafts as drafts_mod
    import draftloop_api.routes.edits as edits_mod

    drafts_mod._store = None
    edits_mod._store = None
    return TestClient(create_app())


def test_get_draft_404_when_missing(client):
    r = client.get("/api/matters/M-1/drafts/D-1")
    assert r.status_code == 404


def test_post_edits_persists(client):
    r = client.post(
        "/api/matters/M-1/drafts/D-1/edits",
        json={"edits": [{"event_id": "ulid-1", "op": "fact_text_changed"}]},
    )
    assert r.status_code == 202
    assert r.json()["accepted"] == 1
    r2 = client.post(
        "/api/matters/M-1/drafts/D-1/edits",
        json={"edits": [{"event_id": "ulid-2", "op": "citation_added"}]},
    )
    assert r2.headers["ETag"] == '"2"'


def test_post_edits_rejects_non_list(client):
    r = client.post(
        "/api/matters/M-1/drafts/D-1/edits",
        json={"edits": "not a list"},
    )
    assert r.status_code == 400


def test_get_draft_returns_stored_payload(client, tmp_path):
    # Seed the store directly via SQLite path.
    import asyncio
    import draftloop_api.routes.drafts as drafts_mod

    async def _seed():
        store = drafts_mod._get_store()
        await store.init_schema()
        await store.put("drafts/M-1/D-1", {"summary": {"parties": []}})

    asyncio.run(_seed())
    r = client.get("/api/matters/M-1/drafts/D-1")
    assert r.status_code == 200
    assert r.json()["summary"]["parties"] == []
