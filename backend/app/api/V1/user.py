# backend/app/api/V1/users.py
from __future__ import annotations
from typing import List, Optional
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.app.repositories.users_repo import find_by_id as find_user_by_id
from backend.app.schemas.user import UserPublic, UserResetPasswordRequest, UserCreate, UserUpdate
from backend.app.deps.auth import get_current_user
from backend.app.repositories.users_repo import list_users, delete_user, update_password, find_by_email, create_user_extended
from backend.app.core.rbac_policies import get_resource_access
from backend.app.core.security import hash_password


class UserCreateExtended(BaseModel):
    """Extended user creation schema matching frontend expectations"""
    email: EmailStr
    displayName: Optional[str] = None
    roleKey: str = "user"
    locale: Optional[str] = None
    sendInvite: bool = True


class UserPublicExtended(UserPublic):
    """Extended user public schema with displayName"""
    displayName: Optional[str] = None
    locale: Optional[str] = None
    isDisabled: Optional[bool] = None
    tempPassword: Optional[str] = None


router = APIRouter()
RESOURCE = "users"


@router.get("/users", response_model=List[UserPublicExtended])
async def users_index(skip: int = 0, limit: int = 50, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canView", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    docs = await list_users(limit=limit, skip=skip)
    out: List[UserPublicExtended] = []
    for d in docs:
        out.append(UserPublicExtended(
            id=str(d["_id"]),
            email=d["email"],
            roleKey=d.get("roleKey", "user"),
            displayName=d.get("displayName"),
            locale=d.get("locale"),
            isDisabled=d.get("isDisabled", False),
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
async def users_reset_password(user_id: str, payload: UserResetPasswordRequest, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not (access.get("canUpdate") or access.get("canManagePermissions")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    new_hash = hash_password(payload.new_password)
    ok = await update_password(user_id, new_hash)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None


@router.post("/users", response_model=UserPublicExtended, status_code=201)
async def users_create(payload: UserCreateExtended, user: dict = Depends(get_current_user)):
    """Create a new user. If sendInvite is False, generates a temp password."""
    access = await get_resource_access(user, RESOURCE)
    if not (access.get("canCreate") or access.get("canManagePermissions")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    # uniqueness check
    if await find_by_email(payload.email):
        raise HTTPException(status_code=409, detail="User already exists")
    
    # Generate password
    temp_password = None
    if payload.sendInvite:
        # TODO: In production, send invite email instead
        # For now, generate temp password even if sendInvite is True
        temp_password = secrets.token_urlsafe(12)
    else:
        temp_password = secrets.token_urlsafe(12)
    
    password_hash = hash_password(temp_password)
    
    # Create user with extended fields
    new_id = await create_user_extended(
        email=payload.email,
        password_hash=password_hash,
        role_key=payload.roleKey,
        locale=payload.locale,
        display_name=payload.displayName,
        restaurant_id=user.get("restaurantId", "default")
    )
    
    doc = await find_user_by_id(new_id)
    return UserPublicExtended(
        id=str(doc["_id"]),
        email=doc["email"],
        roleKey=doc.get("roleKey", "user"),
        displayName=doc.get("displayName"),
        locale=doc.get("locale"),
        isDisabled=doc.get("isDisabled", False),
        tempPassword=temp_password
    )


@router.get("/users/{user_id}", response_model=UserPublicExtended)
async def users_get(user_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canView"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    doc = await find_user_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublicExtended(
        id=str(doc["_id"]),
        email=doc["email"],
        roleKey=doc.get("roleKey", "user"),
        displayName=doc.get("displayName"),
        locale=doc.get("locale"),
        isDisabled=doc.get("isDisabled", False),
    )


@router.put("/users/{user_id}", response_model=UserPublicExtended)
@router.patch("/users/{user_id}", response_model=UserPublicExtended)
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

    doc = await find_user_by_id(user_id)
    return UserPublicExtended(
        id=str(doc["_id"]),
        email=doc["email"],
        roleKey=doc.get("roleKey", "user"),
        displayName=doc.get("displayName"),
        locale=doc.get("locale"),
        isDisabled=doc.get("isDisabled", False),
    )
