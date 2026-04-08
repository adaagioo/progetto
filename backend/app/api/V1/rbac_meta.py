# backend/app/api/V1/rbac_meta.py
from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.rbac_policies import (
	list_resources, list_capabilities, get_role_policies,
	_DEFAULT_POLICIES, _RESOURCES, _CAPABILITIES
)
from backend.app.deps.auth import get_current_user
from backend.app.core import rbac_policies as rbac
from backend.app.db.mongo import get_db

router = APIRouter()


def _roles_col():
	return get_db()["rbac_custom_roles"]


# Role display names
_ROLE_NAMES = {
	"owner": "Owner",
	"admin": "Administrator",
	"manager": "Manager",
	"staff": "Staff",
	"user": "User",
}

# Resource display names
_RESOURCE_NAMES = {
	"users": "Users",
	"ingredients": "Ingredients",
	"preparations": "Preparations",
	"recipes": "Recipes",
	"inventory": "Inventory",
	"exports": "Exports",
	"rbac": "Access Control",
	"files": "Files",
	"ocr": "OCR/Document Import",
	"receiving": "Receiving",
	"suppliers": "Suppliers",
	"menu": "Menu",
	"prep-list": "Prep List",
	"order-list": "Order List",
	"sales": "Sales",
	"wastage": "Wastage",
	"pl": "Profit & Loss",
	"restaurant": "Restaurant Settings",
	"dashboard": "Dashboard",
}


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
	"""
	Get list of resources with their available actions.
	Returns format expected by frontend: array of {key, name, actions}
	"""
	# Standard actions for all resources
	standard_actions = ["canView", "canCreate", "canUpdate", "canDelete"]

	resources = []
	for res_key in _RESOURCES:
		resources.append({
			"key": res_key,
			"name": _RESOURCE_NAMES.get(res_key, res_key.replace("-", " ").title()),
			"actions": standard_actions
		})

	return resources


@router.get("/rbac/roles")
async def rbac_roles(user: dict = Depends(get_current_user)):
	"""
	Get list of roles with their permissions.
	Returns format expected by frontend: array of {roleKey, roleName, permissions, isCustomized}
	"""
	restaurant_id = user.get("restaurantId")

	# Load custom permissions from DB
	custom_permissions = {}
	if restaurant_id:
		cursor = _roles_col().find({"restaurantId": restaurant_id})
		async for doc in cursor:
			custom_permissions[doc["roleKey"]] = doc.get("permissions", {})

	roles = []
	for role_key, default_perms in _DEFAULT_POLICIES.items():
		# Skip 'owner' role from UI
		if role_key == "owner":
			continue

		# Convert permissions from {resource: {cap: bool}} to {resource: [caps]}
		permissions = {}
		is_customized = role_key in custom_permissions

		# Use custom permissions if available, otherwise use defaults
		source_perms = custom_permissions.get(role_key, default_perms)

		for resource, caps in source_perms.items():
			if isinstance(caps, dict):
				# Convert {canView: True, canCreate: False} to ["canView"]
				permissions[resource] = [cap for cap, enabled in caps.items() if enabled]
			elif isinstance(caps, list):
				# Already in list format
				permissions[resource] = caps

		roles.append({
			"roleKey": role_key,
			"roleName": _ROLE_NAMES.get(role_key, role_key.title()),
			"permissions": permissions,
			"isCustomized": is_customized
		})

	return roles


@router.put("/rbac/roles/{role_key}/permissions")
async def update_role_permissions(
	role_key: str,
	permissions: Dict[str, List[str]],
	user: dict = Depends(get_current_user)
):
	"""
	Update permissions for a role.
	Permissions format: {resource: [cap1, cap2, ...]}
	"""
	# Check if user has permission to manage RBAC
	access = await rbac.get_resource_access(user, "rbac")
	if not access.get("canUpdate") and not access.get("canManagePermissions"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	# Validate role exists
	if role_key not in _DEFAULT_POLICIES:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_key}' not found")

	# Save custom permissions to DB
	await _roles_col().update_one(
		{"restaurantId": restaurant_id, "roleKey": role_key},
		{"$set": {
			"restaurantId": restaurant_id,
			"roleKey": role_key,
			"permissions": permissions
		}},
		upsert=True
	)

	return {"success": True, "roleKey": role_key}


@router.post("/rbac/roles/{role_key}/reset")
async def reset_role_permissions(
	role_key: str,
	user: dict = Depends(get_current_user)
):
	"""
	Reset role permissions to defaults by removing custom permissions.
	"""
	# Check if user has permission to manage RBAC
	access = await rbac.get_resource_access(user, "rbac")
	if not access.get("canUpdate") and not access.get("canManagePermissions"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	restaurant_id = user.get("restaurantId")
	if not restaurant_id:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no restaurant assigned")

	# Validate role exists
	if role_key not in _DEFAULT_POLICIES:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_key}' not found")

	# Delete custom permissions from DB
	result = await _roles_col().delete_one({
		"restaurantId": restaurant_id,
		"roleKey": role_key
	})

	return {"success": True, "roleKey": role_key, "wasCustomized": result.deleted_count > 0}
