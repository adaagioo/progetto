from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .core.config import settings
from .db.indexes import ensure_indexes
from .db.mongo import init_mongo, close_mongo
from .api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_mongo()
    await ensure_indexes()
    yield
    # Shutdown
    await close_mongo()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOW_METHODS,
        allow_headers=settings.ALLOW_HEADERS,
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
