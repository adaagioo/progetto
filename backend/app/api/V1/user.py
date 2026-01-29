# backend/app/api/V1/users.py
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.repositories.users_repo import find_by_id
from backend.app.schemas.user import UserPublic, UserResetPasswordRequest, UserCreate, UserUpdate, UserCreateResponse
import secrets
from backend.app.deps.auth import get_current_user
from backend.app.repositories.users_repo import list_users, delete_user, update_password, find_by_email, create_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.core.security import hash_password
from backend.app.repositories.password_reset_repo import pr_create
from backend.app.services.email_service import send_email, reset_password_email


router = APIRouter()
RESOURCE = "users"


@router.get("/users", response_model=List[UserPublic])
async def users_index(skip: int = 0, limit: int = 50, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	docs = await list_users(limit=limit, skip=skip)
	out: List[UserPublic] = []
	for d in docs:
		out.append(UserPublic(
			id=str(d["_id"]),
			email=d["email"],
			roleKey=d.get("roleKey", "user"),
			displayName=d.get("displayName"),
			locale=d.get("locale"),
			isDisabled=d.get("isDisabled", False),
			lastLoginAt=d.get("lastLoginAt"),
		))
	return out


@router.delete("/users/{user_id}", status_code=204)
async def users_delete(user_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok = await delete_user(user_id)
	if not ok:
		raise HTTPException(status_code=404, detail="User not found")
	return None


@router.post("/users/{user_id}/reset-password", status_code=204)
async def users_reset_password(
	user_id: str,
	payload: Optional[UserResetPasswordRequest] = None,
	user: dict = Depends(get_current_user)
):
	"""Reset user password - either directly set new password or send reset email"""
	access = await get_resource_access(user, RESOURCE)
	if not (access.get("canUpdate") or access.get("canManagePermissions")):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	target_user = await find_by_id(user_id)
	if not target_user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	if payload and payload.new_password:
		# Admin directly sets new password
		new_hash = hash_password(payload.new_password)
		ok = await update_password(user_id, new_hash)
		if not ok:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	else:
		# Send password reset email
		token = await pr_create(user_id, target_user["email"])
		subject, plain_body, html_body = reset_password_email(
			to_email=target_user["email"],
			token=token,
			reset_url=None
		)
		send_email(
			to_email=target_user["email"],
			subject=subject,
			body=plain_body,
			html=html_body
		)
	return None


@router.post("/users", response_model=UserCreateResponse, status_code=201)
async def users_create(payload: UserCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not (access.get("canCreate") or access.get("canManagePermissions")):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# uniqueness check
	if await find_by_email(payload.email):
		raise HTTPException(status_code=409, detail="User already exists")

	# Handle password: use provided or generate temp password
	temp_password = None
	if payload.sendInvite or not payload.password:
		# Generate a secure temporary password
		temp_password = secrets.token_urlsafe(12)
		password_to_hash = temp_password
	else:
		password_to_hash = payload.password

	new_id = await create_user(
		payload.email,
		hash_password(password_to_hash),
		role_key=payload.roleKey,
		locale=payload.locale,
		display_name=payload.displayName
	)
	doc = await find_by_id(new_id)

	# Build response
	response = UserCreateResponse(
		id=str(doc["_id"]),
		email=doc["email"],
		roleKey=doc.get("roleKey", "user"),
		displayName=doc.get("displayName"),
		locale=doc.get("locale"),
		isDisabled=doc.get("isDisabled", False),
		lastLoginAt=doc.get("lastLoginAt"),
		tempPassword=temp_password  # Only set if sendInvite was True
	)

	return response


@router.get("/users/{user_id}", response_model=UserPublic)
async def users_get(user_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await find_by_id(user_id)
	if not doc:
		raise HTTPException(status_code=404, detail="User not found")
	return UserPublic(
		id=str(doc["_id"]),
		email=doc["email"],
		roleKey=doc.get("roleKey", "user"),
		displayName=doc.get("displayName"),
		locale=doc.get("locale"),
		isDisabled=doc.get("isDisabled", False),
		lastLoginAt=doc.get("lastLoginAt"),
	)


@router.put("/users/{user_id}", response_model=UserPublic)
@router.patch("/users/{user_id}", response_model=UserPublic)
async def users_update(user_id: str, payload: UserUpdate, user: dict = Depends(get_current_user)):
	"""Update user (email, role, locale)"""
	from backend.app.repositories.users_repo import update_user as repo_update_user

	access = await get_resource_access(user, RESOURCE)
	if not (access.get("canUpdate") or access.get("canManagePermissions")):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# if email is changing, ensure uniqueness
	patch = payload.model_dump(exclude_unset=True)
	if "email" in patch:
		exists = await find_by_email(patch["email"])
		if exists and str(exists["_id"]) != user_id:
			raise HTTPException(status_code=409, detail="Email already in use")

	ok = await repo_update_user(user_id, patch)
	if not ok:
		raise HTTPException(status_code=404, detail="User not found")

	doc = await find_by_id(user_id)
	return UserPublic(
		id=str(doc["_id"]),
		email=doc["email"],
		roleKey=doc.get("roleKey", "user"),
		displayName=doc.get("displayName"),
		locale=doc.get("locale"),
		isDisabled=doc.get("isDisabled", False),
		lastLoginAt=doc.get("lastLoginAt"),
	)
