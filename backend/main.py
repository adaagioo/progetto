from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.db.indexes import ensure_indexes
from backend.app.db.mongo import init_mongo, close_mongo
from backend.app.api.router import api_router
from backend.app.schemas.ocr import rebuild_models as rebuild_ocr_models

TAGS_METADATA = [
	{"name": "Auth", "description": "Login, refresh, password reset, ecc."},
	{"name": "Ingredients", "description": "CRUD ingredienti e ricerca."},
	{"name": "Inventory", "description": "Gestione inventario, stock e mapping OCR."},
	{"name": "Files", "description": "Upload/download e metadati."},
	{"name": "OCR", "description": "OCR, parsing e suggerimenti inventario."},
]

app = FastAPI(
	title="RistoBrain API",
	version="1.0.0",
	description="API per gestione ricette, inventario, OCR e parsing documenti.",
	contact={"name": "Team RistoBrain", "email": "dev@example.org"},
	license_info={"name": "Proprietary"},
	openapi_tags=TAGS_METADATA,
	docs_url="/docs",  # Swagger UI
	redoc_url="/redoc",  # ReDoc
	openapi_url="/openapi.json",  # schema OpenAPI puro
)


@app.on_event("startup")
async def _rebuild_pydantic_models() -> None:
	rebuild_ocr_models()


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

	app.include_router(api_router)

	return app


app = create_app()
