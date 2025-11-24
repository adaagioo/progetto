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
	{
		"name": "health",
		"description": "Health check endpoints for monitoring application and database status"
	},
	{
		"name": "auth",
		"description": "Authentication and authorization: login, token refresh, password reset, user registration"
	},
	{
		"name": "users",
		"description": "User management and profile operations"
	},
	{
		"name": "rbac",
		"description": "Role-Based Access Control: permissions, roles, and resource access management"
	},
	{
		"name": "ingredients",
		"description": "Ingredient catalog: CRUD operations, price history, and supplier relationships"
	},
	{
		"name": "inventory",
		"description": "Inventory management: stock levels, valuation, adjustments, and expiring items tracking"
	},
	{
		"name": "receiving",
		"description": "Receiving operations: record deliveries, manage supplier orders, and auto-update inventory"
	},
	{
		"name": "suppliers",
		"description": "Supplier management: contact info, documents, and default settings"
	},
	{
		"name": "recipes",
		"description": "Recipe management: ingredients list, preparation steps, costing, and yield"
	},
	{
		"name": "preparations",
		"description": "Prep items: batch cooking, mise en place, and intermediate products"
	},
	{
		"name": "production",
		"description": "Production planning: daily menu plans, forecasting, and batch scheduling"
	},
	{
		"name": "orders",
		"description": "Order list generation: automatic reorder suggestions based on consumption forecasts"
	},
	{
		"name": "sales",
		"description": "Sales tracking: daily revenue, item sales, and automatic inventory deduction"
	},
	{
		"name": "wastage",
		"description": "Waste tracking: spoilage, overproduction, and loss management"
	},
	{
		"name": "pl",
		"description": "Profit & Loss: financial snapshots, COGS, OPEX, labor costs, and EBITDA calculation"
	},
	{
		"name": "menu",
		"description": "Menu management: item catalog, pricing, and availability"
	},
	{
		"name": "dashboard",
		"description": "Dashboard metrics and KPIs for operational insights"
	},
	{
		"name": "restaurant",
		"description": "Restaurant settings and configuration"
	},
	{
		"name": "files",
		"description": "File management: upload, download, and metadata for documents and images"
	},
	{
		"name": "ocr",
		"description": "OCR and document parsing: invoice processing, automatic data extraction, and smart mapping"
	},
	{
		"name": "exports",
		"description": "Data export functionality: CSV, Excel, and report generation"
	},
	{
		"name": "dependencies",
		"description": "Dependency tracking between recipes, inventory, and other entities"
	},
]

app = FastAPI(
	title="RistoBrain API",
	version="2.0.0",
	description="""
	## RistoBrain Restaurant Management System

	Complete API for restaurant back-office operations including:

	* 📦 **Inventory Management** - Real-time stock tracking with automatic valuation
	* 🧾 **Receiving & Orders** - Supplier management and smart reorder suggestions
	* 👨‍🍳 **Production Planning** - Recipe costing, prep lists, and batch scheduling
	* 📊 **Sales & Wastage** - Track revenue and losses with automatic inventory updates
	* 💰 **P&L Analytics** - Financial insights with COGS, OPEX, and profitability metrics
	* 🤖 **OCR Intelligence** - Auto-extract data from invoices and delivery notes
	* 🔐 **RBAC Security** - Fine-grained permissions and role management

	All endpoints support **JSON** format and require **JWT authentication** (except auth endpoints).
	""",
	contact={"name": "RistoBrain Support", "email": "support@ristobrain.com"},
	license_info={"name": "Proprietary"},
	openapi_tags=TAGS_METADATA,
	docs_url="/docs",  # Swagger UI
	redoc_url="/redoc",  # ReDoc
	openapi_url="/openapi.json",  # OpenAPI schema
	swagger_ui_parameters={
		"defaultModelsExpandDepth": -1,  # Hide schemas by default
		"docExpansion": "none",  # Collapse all endpoints by default
		"filter": True,  # Enable search filter
		"showCommonExtensions": True,
	}
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

	app.include_router(api_router, prefix="/api")

	return app


app = create_app()
