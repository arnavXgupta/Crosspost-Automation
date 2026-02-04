from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.routes import router as v1_router
from app.config import get_settings
from app.observability.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Content Distribution API", version="0.1.0")
    app.include_router(v1_router)
    return app


app = create_app()

