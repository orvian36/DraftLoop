"""POST /api/matters/:matter_id/drafts/:draft_id/edits route."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from draftloop_core.config import get_settings
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore

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


@router.post("/{draft_id}/edits", status_code=202)
async def post_edits(
    matter_id: str, draft_id: str, request: Request, response: Response
) -> dict[str, Any]:
    body = await request.json()
    events = body.get("edits") or []
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="edits must be a list")
    store = _get_store()
    await store.init_schema()
    key = f"edits/{matter_id}/{draft_id}"
    existing = await store.get(key) or []
    existing.extend(events)
    await store.put(key, existing)
    response.headers["ETag"] = f'"{len(existing)}"'
    return {"batch_id": f"batch_{int(time.time())}", "accepted": len(events)}
