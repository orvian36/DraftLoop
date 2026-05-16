import pytest
from draftloop_api.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from draftloop_api.wiring import reset_singletons
    from draftloop_core.config import get_settings

    get_settings.cache_clear()
    reset_singletons()
    import draftloop_api.routes.drafts as drafts_mod
    import draftloop_api.routes.edits as edits_mod

    drafts_mod._store = None
    edits_mod._store = None
    return TestClient(create_app())


def test_matters_starts_empty(client):
    assert client.get("/api/matters").json() == {"matters": []}


def test_upload_doc_appears_in_matter_list(client):
    files = {"file": ("complaint.pdf", b"%PDF-1.4 fake", "application/pdf")}
    r = client.post("/api/matters/M-001/docs", files=files)
    assert r.status_code == 202
    assert r.json() == {"doc_id": "complaint.pdf", "status": "uploaded"}
    matters = client.get("/api/matters").json()["matters"]
    assert "M-001" in matters


def test_get_matter_includes_uploaded_doc(client):
    client.post(
        "/api/matters/M-002/docs",
        files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
    )
    r = client.get("/api/matters/M-002")
    body = r.json()
    assert body["matter_id"] == "M-002"
    assert len(body["docs"]) == 1


def test_admin_endpoints_return_empty_lists(client):
    assert client.get("/admin/rules").json() == {"rules": []}
    assert client.get("/admin/replay").json() == {"reports": []}
    assert client.get("/admin/edits").json() == {"total_events": 0}


def test_upload_requires_filename(client):
    files = {"file": ("", b"data", "application/pdf")}
    r = client.post("/api/matters/M-1/docs", files=files)
    # FastAPI's multipart validator rejects empty filenames as 422 before our handler runs.
    assert r.status_code in (400, 422)
