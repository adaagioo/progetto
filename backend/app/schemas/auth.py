# backend/app/schemas/auth.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


class UserData(BaseModel):
	"""User data returned on login/register"""
	model_config = ConfigDict(extra="ignore")
	id: str
	email: str
	roleKey: str
	restaurantId: str
	locale: Optional[str] = None


class TokenResponse(BaseModel):
	access_token: str
	refresh_token: Optional[str] = None
	user: Optional[UserData] = None


class RegisterRequest(BaseModel):
	email: EmailStr
	password: str = Field(
		...,
		min_length=8,
		max_length=128,
		description="Password must be between 8 and 128 characters"
	)
	locale: str | None = None


class MeResponse(BaseModel):
	id: str
	email: EmailStr
	roleKey: str
	locale: str | None = None


class ForgotPasswordRequest(BaseModel):
	email: EmailStr


class ResetPasswordRequest(BaseModel):
	token: str
	new_password: str = Field(
		...,
		min_length=8,
		max_length=128,
		description="Password must be between 8 and 128 characters"
	)


class LocaleUpdateRequest(BaseModel):
	locale: str
