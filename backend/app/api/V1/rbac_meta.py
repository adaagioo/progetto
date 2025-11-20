# backend/app/api/V1/rbac_meta.py
from __future__ import annotations
from fastapi import APIRouter, Depends

from backend.app.core.rbac_policies import list_resources, list_capabilities, get_role_policies
from backend.app.deps.auth import get_current_user
from backend.app.core import rbac_policies as rbac

router = APIRouter()


def _safe_get(attr: str, default):
	return getattr(rbac, attr, default)


@router.get("/rbac/meta")
async def rbac_meta(user: dict = Depends(get_current_user)):
	resources = _safe_get("RESOURCES", [])
	actions = _safe_get("ACTIONS", ["canView", "canCreate", "canUpdate", "canDelete"])
	role_matrix = _safe_get("ROLE_MATRIX", {})
	eff = {}
	get_access = getattr(rbac, "get_resource_access", None)
	if callable(get_access):
		for res in resources or role_matrix.keys():
			try:
				eff[res] = await get_access(user, res)
			except TypeError:
				eff[res] = get_access(user, res)
	return {"resources": list(resources) if resources else list(role_matrix.keys()), "actions": actions,
	        "roles": role_matrix, "effective": eff}


@router.get("/rbac/resources")
async def rbac_resources(user: dict = Depends(get_current_user)):
	# Note: This endpoint is accessible to all authenticated users for introspection.
	# Could be restricted to admins in the future if needed.
	return {"resources": list_resources(), "capabilities": list_capabilities()}


@router.get("/rbac/roles")
async def rbac_roles(user: dict = Depends(get_current_user)):
	return {"roles": get_role_policies()}
