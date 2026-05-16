"""Read-only admin endpoints (rules, replay reports, edit-event count)."""

from __future__ import annotations

from fastapi import APIRouter

from draftloop_api.wiring import document_store

router = APIRouter(prefix="/admin")


@router.get("/rules")
async def list_rules() -> dict:
    store = document_store()
    await store.init_schema()
    rules: list[dict] = []
    async for _, v in store.list("rules/"):
        rules.append(v)
    return {"rules": rules}


@router.get("/replay")
async def list_replays() -> dict:
    store = document_store()
    await store.init_schema()
    out: list[dict] = []
    async for _, v in store.list("replay_reports/"):
        out.append(v)
    return {"reports": out}


@router.get("/edits")
async def edit_summary() -> dict:
    store = document_store()
    await store.init_schema()
    n = 0
    async for _ in store.list("edit_events/"):
        n += 1
    return {"total_events": n}
