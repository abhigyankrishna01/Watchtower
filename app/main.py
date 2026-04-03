from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db


def create_app() -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.auto_create_db:
            init_db()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.include_router(router)

    Instrumentator().instrument(app).expose(app, endpoint=settings.prometheus_metrics_path)

    return app


app = create_app()
