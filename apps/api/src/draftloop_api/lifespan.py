"""FastAPI lifespan: startup/shutdown hooks (logging, settings warm-up)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from draftloop_core.config import get_settings
from draftloop_core.obs import configure_logging, get_logger

logger = get_logger("draftloop.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.started_at = time.monotonic()
    logger.info("api.startup", drafter_model=settings.drafter_model)
    yield
    logger.info("api.shutdown")
