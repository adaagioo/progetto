# backend/app/api/V1/rbac_admin.py
from __future__ import annotations

from typing import List, Any, Dict

from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.deps.auth import get_current_user
from backend.app.db.mongo import get_db
from backend.app.core.rbac_policies import get_resource_access
from backend.app.core import rbac_policies as policies
from backend.app.schemas.rbac import RoleDefinition, ResourceCapabilities

router = APIRouter()
RESOURCE = "rbac_admin"

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
	if user.get("roleKey") != "admin":
		raise HTTPException(status_code=403, detail="Admin only")
	db = get_db()
	for role_key, permissions in DEFAULTS.items():
		await db["rbac_roles"].update_one(
			{"roleKey": role_key},
			{"$set": {"roleKey": role_key, "permissions": permissions}},
			upsert=True,
		)
	return {"ok": True, "seeded_roles": list(DEFAULTS.keys())}


def _require_admin(access: Dict[str, Any]):
	if not access.get("canUpdate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/rbac/meta/roles", response_model=List[RoleDefinition])
async def rbac_list_roles(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	roles = await policies.list_roles()
	out: List[RoleDefinition] = []
	for r in roles:
		grants = []
		for g in r.get("grants", []):
			grants.append(ResourceCapabilities(resource=g["resource"], capabilities=g.get("capabilities", {})))
		out.append(RoleDefinition(role=r["role"], grants=grants))
	return out


@router.get("/rbac/meta/capabilities/{role}/{resource}", response_model=ResourceCapabilities)
async def rbac_get_caps(role: str, resource: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	caps = await policies.get_capabilities_for_role(role, resource)
	if caps is None:
		raise HTTPException(status_code=404, detail="Role not found")
	return ResourceCapabilities(resource=resource, capabilities=caps or {})


@router.put("/rbac/meta/roles/{role}", status_code=204)
async def rbac_put_role(role: str, body: RoleDefinition, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	_require_admin(access)
	grants = [{"resource": g.resource, "capabilities": g.capabilities} for g in body.grants]
	ok = await policies.upsert_role(role, grants)
	if not ok:
		raise HTTPException(status_code=500, detail="Failed to upsert role")
	return
