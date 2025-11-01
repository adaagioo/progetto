# backend/app/core/rbac_utils.py
from __future__ import annotations

from typing import Dict, Any
from app.core.rbac_schema import Resource, Action, DEFAULT_PERMISSIONS, has_permission, merge_permissions
from app.db.mongo import get_db

async def get_user_permissions(current_user: dict) -> dict:
    """Compute effective permissions for a user.
    - Loads role-based defaults from rbac_roles collection (if any override),
      otherwise falls back to DEFAULT_PERMISSIONS from schema.
    - Applies restaurant-specific overrides from rbac_overrides collection.
    """
    db = get_db()
    role_key = current_user.get("role", "guest")
    restaurant_id = current_user.get("restaurantId")

    # Default permissions: either stored in DB or static defaults
    role_doc = await db["rbac_roles"].find_one({"roleKey": role_key}) or {}
    default = role_doc.get("permissions") or DEFAULT_PERMISSIONS.get(role_key, {})

    # Restaurant overrides (per role, per restaurant)
    overrides_doc = await db["rbac_overrides"].find_one({"roleKey": role_key, "restaurantId": restaurant_id}) or {}
    overrides = overrides_doc.get("permissions", {})

    return merge_permissions(default, overrides)

async def get_resource_access(current_user: dict, resource: str) -> Dict[str, bool]:
    perms = await get_user_permissions(current_user)
    return {
        "canView": has_permission(perms, resource, Action.VIEW),
        "canCreate": has_permission(perms, resource, Action.CREATE),
        "canUpdate": has_permission(perms, resource, Action.UPDATE),
        "canDelete": has_permission(perms, resource, Action.DELETE),
    }
