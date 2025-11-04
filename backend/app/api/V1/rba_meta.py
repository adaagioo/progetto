# backend/app/api/V1/rbac_meta.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import list_resources, list_capabilities, get_role_policies

router = APIRouter()


@router.get("/rbac/resources")
async def rbac_resources(user: dict = Depends(get_current_user)):
	# TODO (af): We could restrict this to admins if desired; for now, any authenticated user can introspect.
	return {"resources": list_resources(), "capabilities": list_capabilities()}


@router.get("/rbac/roles")
async def rbac_roles(user: dict = Depends(get_current_user)):
	return {"roles": get_role_policies()}
