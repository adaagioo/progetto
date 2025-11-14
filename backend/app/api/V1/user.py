# backend/app/api/V1/users.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.repositories.inventory_repo import find_by_id
from backend.app.schemas.user import UserPublic, UserResetPasswordRequest, UserCreate, UserUpdate
from backend.app.deps.auth import get_current_user
from backend.app.repositories.users_repo import list_users, delete_user, update_password, find_by_email, create_user
from backend.app.core.rbac_utils import get_resource_access
from backend.app.core.security import hash_password


router = APIRouter()
RESOURCE = "users"


@router.get("/users", response_model=List[UserPublic])
async def users_index(skip: int = 0, limit: int = 50, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	docs = await list_users(limit=limit, skip=skip)
	out: List[UserPublic] = []
	for d in docs:
		out.append(UserPublic(
			id=str(d["_id"]),
			email=d["email"],
			roleKey=d.get("roleKey", "user"),
		))
	return out


@router.delete("/users/{user_id}", status_code=204)
async def users_delete(user_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canDelete"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	ok = await delete_user(user_id)
	if not ok:
		raise HTTPException(status_code=404, detail="User not found")
	return None


@router.post("/users/{user_id}/reset-password", status_code=204)
async def users_reset_password(user_id: str, payload: UserResetPasswordRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not (access.get("canUpdate") or access.get("canManagePermissions")):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	new_hash = hash_password(payload.new_password)
	ok = await update_password(user_id, new_hash)
	if not ok:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	return None


@router.post("/users", response_model=UserPublic, status_code=201)
async def users_create(payload: UserCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not (access.get("canCreate") or access.get("canManagePermissions")):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	# uniqueness check
	if await find_by_email(payload.email):
		raise HTTPException(status_code=409, detail="User already exists")
	new_id = await create_user(payload.email, hash_password(payload.password), role_key=payload.roleKey,
	                           locale=payload.locale)
	doc = await find_by_id(new_id)
	return UserPublic(id=str(doc["_id"]), email=doc["email"], roleKey=doc.get("roleKey", "user"))


@router.get("/users/{user_id}", response_model=UserPublic)
async def users_get(user_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await find_by_id(user_id)
	if not doc:
		raise HTTPException(status_code=404, detail="User not found")
	return UserPublic(id=str(doc["_id"]), email=doc["email"], roleKey=doc.get("roleKey", "user"))


# @router.put("/users/{user_id}", response_model=UserPublic)
# async def users_update(user_id: str, payload: UserUpdate, user: dict = Depends(get_current_user)):
# 	access = await get_resource_access(user, RESOURCE)
# 	if not (access.get("canUpdate") or access.get("canManagePermissions")):
# 		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
# 	# if email is changing, ensure uniqueness
# 	patch = payload.model_dump(exclude_unset=True)
# 	if "email" in patch:
# 		exists = await find_by_email(patch["email"])
# 		if exists and str(exists["_id"]) != user_id:
# 			raise HTTPException(status_code=409, detail="Email already in use")
# 	ok = await repo_update_user(user_id, patch)
# 	if not ok:
# 		raise HTTPException(status_code=404, detail="User not found")
# 	doc = await find_by_id(user_id)
# 	return UserPublic(id=str(doc["_id"]), email=doc["email"], roleKey=doc.get("roleKey", "user"))
