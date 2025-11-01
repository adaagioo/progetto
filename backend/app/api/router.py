# backend/app/api/router.py
from __future__ import annotations
from fastapi import APIRouter

api_router = APIRouter()

# Wire V1 modules if present
try:
    from .V1 import health
    api_router.include_router(health.router, prefix="/v1", tags=["health"])
except Exception:
    pass

for mod, tag in [
    ("rbac", "rbac"),
    ("ingredients", "ingredients"),
    ("inventory", "inventory"),
    ("preparations", "preparations"),
    ("recipes", "recipes"),
    ("exports", "exports"),
    ("rbac_admin", "rbac-admin"),
    ("auth", "auth"),
]:
    try:
        module = __import__(f"app.api.V1.{mod}", fromlist=["router"])
        api_router.include_router(module.router, prefix="/v1", tags=[tag])
    except Exception:
        continue
