from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    started = getattr(request.app.state, "started_at", time.monotonic())
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - started),
    }
