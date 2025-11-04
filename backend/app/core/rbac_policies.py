# backend/app/core/rbac_policies.py
from __future__ import annotations
from typing import Dict, Any, List

# Define supported capabilities
_CAPABILITIES = ["canView", "canCreate", "canUpdate", "canDelete", "canManagePermissions"]

# Define resources exposed by the API
_RESOURCES = [
	"users", "ingredients", "preparations", "recipes", "inventory", "exports",
	"rbac", "files", "ocr", "receiving", "suppliers", "menu", "prep-list",
	"order-list", "sales", "wastage", "pl", "restaurant", "dashboard"
]

# Role policy map: roleKey -> resource -> caps
_DEFAULT_POLICIES: Dict[str, Dict[str, Dict[str, bool]]] = {
	"owner": {r: {c: True for c in _CAPABILITIES} for r in _RESOURCES},
	"admin": {
		**{r: {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": True, "canManagePermissions": True}
		   for r in _RESOURCES if r != "rbac"},
		"rbac": {"canView": True, "canCreate": False, "canUpdate": True, "canDelete": False,
		         "canManagePermissions": True},
	},
	"manager": {
		"users": {"canView": True, "canCreate": False, "canUpdate": True, "canDelete": False,
		          "canManagePermissions": False},
		"ingredients": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		                "canManagePermissions": False},
		"preparations": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		                 "canManagePermissions": False},
		"recipes": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		            "canManagePermissions": False},
		"inventory": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		              "canManagePermissions": False},
		"exports": {"canView": True, "canCreate": False, "canUpdate": False, "canDelete": False,
		            "canManagePermissions": False},
		"rbac": {"canView": False, "canCreate": False, "canUpdate": False, "canDelete": False,
		         "canManagePermissions": False},
		"files": {"canView": True, "canCreate": True, "canUpdate": False, "canDelete": False,
		          "canManagePermissions": False},
		"ocr": {"canView": True, "canCreate": True, "canUpdate": False, "canDelete": False,
		        "canManagePermissions": False},
		"receiving": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		              "canManagePermissions": False},
		"suppliers": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		              "canManagePermissions": False},
		"menu": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		         "canManagePermissions": False},
		"prep-list": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		              "canManagePermissions": False},
		"order-list": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		               "canManagePermissions": False},
		"sales": {"canView": True, "canCreate": False, "canUpdate": False, "canDelete": False,
		          "canManagePermissions": False},
		"wastage": {"canView": True, "canCreate": True, "canUpdate": False, "canDelete": False,
		            "canManagePermissions": False},
		"pl": {"canView": True, "canCreate": False, "canUpdate": False, "canDelete": False,
		       "canManagePermissions": False},
		"restaurant": {"canView": True, "canCreate": True, "canUpdate": True, "canDelete": False,
		               "canManagePermissions": False},
		"dashboard": {"canView": True, "canCreate": False, "canUpdate": False, "canDelete": False,
		              "canManagePermissions": False},
	},
	"staff": {
		# read-mostly
		**{r: {"canView": True, "canCreate": False, "canUpdate": False, "canDelete": False,
		       "canManagePermissions": False} for r in _RESOURCES},
		"users": {"canView": False, "canCreate": False, "canUpdate": False, "canDelete": False,
		          "canManagePermissions": False},
	},
	"user": {
		# minimal default
		**{r: {"canView": False, "canCreate": False, "canUpdate": False, "canDelete": False,
		       "canManagePermissions": False} for r in _RESOURCES},
	},
}


async def get_resource_access(user: dict, resource: str) -> Dict[str, bool]:
	role = (user or {}).get("roleKey", "user")
	return _DEFAULT_POLICIES.get(role, _DEFAULT_POLICIES["user"]).get(resource, {c: False for c in _CAPABILITIES})


def list_resources() -> List[str]:
	return list(_RESOURCES)


def list_capabilities() -> List[str]:
	return list(_CAPABILITIES)


def get_role_policies() -> Dict[str, Any]:
	# Intended for introspection; safe to return
	return _DEFAULT_POLICIES
