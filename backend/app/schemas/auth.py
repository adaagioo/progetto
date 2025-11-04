# backend/app/schemas/auth.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


class TokenResponse(BaseModel):
	accessToken: str
	refreshToken: str | None = None


class RegisterRequest(BaseModel):
	email: EmailStr
	password: str
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
	new_password: str


class LocaleUpdateRequest(BaseModel):
	locale: str
