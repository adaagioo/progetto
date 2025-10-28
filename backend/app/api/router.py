# backend/app/api/router.py
from fastapi import APIRouter
from .V1 import health, auth, rbac

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1", tags=["health"])
api_router.include_router(auth.router, prefix="/v1", tags=["auth"])
api_router.include_router(rbac.router, prefix="/v1", tags=["rbac"])
