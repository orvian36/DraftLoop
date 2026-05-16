"""GET /api/matters/:matter_id/drafts/:draft_id route."""

from __future__ import annotations

from draftloop_core.config import get_settings
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/matters/{matter_id}/drafts")

_store: SqliteDocumentStore | None = None


def _get_store() -> SqliteDocumentStore:
    global _store
    if _store is None:
        settings = get_settings()
        from pathlib import Path

        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        _store = SqliteDocumentStore(f"{settings.data_dir}/draftloop.db")
    return _store


@router.get("/{draft_id}")
async def get_draft(matter_id: str, draft_id: str) -> dict:
    store = _get_store()
    await store.init_schema()
    payload = await store.get(f"drafts/{matter_id}/{draft_id}")
    if payload is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return payload
