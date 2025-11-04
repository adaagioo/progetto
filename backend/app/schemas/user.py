# backend/app/schemas/user.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
	id: str
	email: EmailStr
	roleKey: str


class UserResetPasswordRequest(BaseModel):
	new_password: str


class UserCreate(BaseModel):
	email: EmailStr
	password: str
	roleKey: str = "user"
	locale: str | None = None


class UserUpdate(BaseModel):
	email: EmailStr | None = None
	roleKey: str | None = None
	locale: str | None = None
