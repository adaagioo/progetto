# backend/app/api/router.py
from __future__ import annotations
from fastapi import APIRouter
import importlib

api_router = APIRouter()

MODULES: list[tuple[str, str]] = [
    ("health", "health"),
    ("rbac", "rbac"),
    ("rbac_admin", "rbac"),
    ("rbac_meta", "rbac"),
    ("dependencies", "dependencies"),
    ("ingredients", "ingredients"),
    ("inventory", "inventory"),
    ("inventory_admin", "inventory"),
    ("inventory_valuation", "inventory"),
    ("preparations", "preparations"),
    ("prep_list", "preparations"),
    ("recipes", "recipes"),
    ("order_list", "orders"),
    ("menu", "menu"),
    ("exports", "exports"),
    ("ocr", "ocr"),
    ("files", "files"),
    ("receiving", "receiving"),
    ("suppliers", "suppliers"),
    ("sales", "sales"),
    ("wastage", "wastage"),
    ("pl", "pl"),
    ("dashboard", "dashboard"),
    ("user", "users"),
    ("auth", "auth"),
]

BASE = "backend.app.api.V1"

for mod_name, tag in MODULES:
    try:
        module = importlib.import_module(f"{BASE}.{mod_name}")
        router = getattr(module, "router", None)
        if router is not None:
            api_router.include_router(router, prefix="/v1", tags=[tag])
    except Exception:
        continue
