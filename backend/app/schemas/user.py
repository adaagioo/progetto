# backend/app/schemas/user.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
	id: str
	email: EmailStr
	roleKey: str
	displayName: Optional[str] = None
	locale: Optional[str] = None
	isDisabled: bool = False
	lastLoginAt: Optional[datetime] = None


class UserResetPasswordRequest(BaseModel):
	new_password: str


class UserCreate(BaseModel):
	email: EmailStr
	password: str
	roleKey: str = "user"
	locale: str | None = None
	displayName: str | None = None


class UserUpdate(BaseModel):
	email: EmailStr | None = None
	roleKey: str | None = None
	locale: str | None = None
	restaurantId: str | None = None
	displayName: str | None = None
	isDisabled: bool | None = None
