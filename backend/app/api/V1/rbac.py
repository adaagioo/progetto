# backend/app/api/v1/rbac.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.rbac import RolePermissions
from app.services.rbac_service import get_permissions, set_permissions
from app.deps.auth import get_current_user

router = APIRouter()


@router.get("/rbac/roles/{role_key}", response_model=RolePermissions)
async def get_role(role_key: str):
	perms = await get_permissions(role_key)
	if perms is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
	return RolePermissions(roleKey=role_key, permissions=perms)


@router.post("/rbac/roles/{role_key}")
async def update_role(role_key: str, body: RolePermissions, user: dict = Depends(get_current_user)):
	await set_permissions(role_key, body.permissions)
	return {"success": True}
