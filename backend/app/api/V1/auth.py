# backend/app/api/v1/auth.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import login as login_service

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
	res = await login_service(payload.email, payload.password)
	if not res["ok"]:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
	return TokenResponse(accessToken=res["accessToken"], refreshToken=None)
