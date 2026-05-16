"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from draftloop_api import __version__
from draftloop_api.lifespan import lifespan
from draftloop_api.routes import admin, drafts, edits, health, ingest, matters, version


def create_app() -> FastAPI:
    app = FastAPI(
        title="DraftLoop API",
        version=__version__,
        lifespan=lifespan,
    )
    for r in (
        health.router,
        version.router,
        matters.router,
        ingest.router,
        drafts.router,
        edits.router,
        admin.router,
    ):
        app.include_router(r)
    return app


app = create_app()
