"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from draftloop_api import __version__
from draftloop_api.lifespan import lifespan
from draftloop_api.routes import health, version


def create_app() -> FastAPI:
    app = FastAPI(
        title="DraftLoop API",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(version.router)
    return app


app = create_app()
