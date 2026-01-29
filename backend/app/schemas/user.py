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
	password: str | None = None  # Optional when sendInvite is True
	roleKey: str = "user"
	locale: str | None = None
	displayName: str | None = None
	sendInvite: bool = False  # If True, generate temp password and optionally send invite email


class UserCreateResponse(BaseModel):
	"""Response for user creation - includes tempPassword when sendInvite was used"""
	id: str
	email: EmailStr
	roleKey: str
	displayName: Optional[str] = None
	locale: Optional[str] = None
	isDisabled: bool = False
	lastLoginAt: Optional[datetime] = None
	tempPassword: Optional[str] = None  # Only included when sendInvite was True


class UserUpdate(BaseModel):
	email: EmailStr | None = None
	roleKey: str | None = None
	locale: str | None = None
	restaurantId: str | None = None
	displayName: str | None = None
	isDisabled: bool | None = None
