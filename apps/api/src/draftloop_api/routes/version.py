from __future__ import annotations

from fastapi import APIRouter

from draftloop_api import __version__

router = APIRouter()


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": __version__}
