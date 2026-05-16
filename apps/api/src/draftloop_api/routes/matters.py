"""GET /api/matters and GET /api/matters/:matter_id."""

from __future__ import annotations

from fastapi import APIRouter

from draftloop_api.wiring import document_store

router = APIRouter(prefix="/api/matters")


@router.get("")
async def list_matters() -> dict:
    store = document_store()
    await store.init_schema()
    matter_ids: set[str] = set()
    async for key, _ in store.list("docs/"):
        parts = key.split("/")
        if len(parts) >= 2:
            matter_ids.add(parts[1])
    return {"matters": sorted(matter_ids)}


@router.get("/{matter_id}")
async def get_matter(matter_id: str) -> dict:
    store = document_store()
    await store.init_schema()
    docs: list[dict] = []
    async for key, value in store.list(f"docs/{matter_id}/"):
        docs.append({"key": key, "doc": value})
    drafts: list[dict] = []
    async for key, value in store.list(f"drafts/{matter_id}/"):
        drafts.append({"key": key, "draft": value})
    return {"matter_id": matter_id, "docs": docs, "drafts": drafts}
