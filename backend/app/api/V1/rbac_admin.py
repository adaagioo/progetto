# backend/app/api/V1/rbac_admin.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.deps.auth import get_current_user
from app.db.mongo import get_db

router = APIRouter()

DEFAULTS = {
    "admin": {
        "ingredients": {"view": True, "create": True, "update": True, "delete": True},
        "inventory": {"view": True, "create": True, "update": True, "delete": True},
        "preparations": {"view": True, "create": True, "update": True, "delete": True},
        "recipes": {"view": True, "create": True, "update": True, "delete": True},
        "preplist": {"view": True},
        "orderlist": {"view": True},
    },
    "manager": {
        "ingredients": {"view": True, "create": True, "update": True, "delete": False},
        "inventory": {"view": True, "create": True, "update": True, "delete": False},
        "preparations": {"view": True, "create": True, "update": True, "delete": False},
        "recipes": {"view": True, "create": True, "update": True, "delete": False},
        "preplist": {"view": True},
        "orderlist": {"view": True},
    },
    "staff": {
        "ingredients": {"view": True, "create": False, "update": False, "delete": False},
        "inventory": {"view": True, "create": False, "update": False, "delete": False},
        "preparations": {"view": True, "create": False, "update": False, "delete": False},
        "recipes": {"view": True, "create": False, "update": False, "delete": False},
        "preplist": {"view": False},
        "orderlist": {"view": False},
    },
}

@router.post("/rbac/seed-defaults")
async def seed_defaults(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    db = get_db()
    for role_key, permissions in DEFAULTS.items():
        await db["rbac_roles"].update_one(
            {"roleKey": role_key},
            {"$set": {"roleKey": role_key, "permissions": permissions}},
            upsert=True,
        )
    return {"ok": True, "seeded_roles": list(DEFAULTS.keys())}
