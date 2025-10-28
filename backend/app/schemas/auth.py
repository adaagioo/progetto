# backend/app/schemas/auth.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


class TokenResponse(BaseModel):
	accessToken: str
	refreshToken: str | None = None
