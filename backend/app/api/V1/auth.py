# backend/app/api/v1/auth.py
from __future__ import annotations

from datetime import datetime

from backend.app.repositories.password_reset_repo import pr_find, pr_create, pr_used
from backend.app.services.auth_service import login as login_service
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.schemas.auth import (
	LoginRequest, TokenResponse, RegisterRequest, MeResponse,
	ForgotPasswordRequest, ResetPasswordRequest, LocaleUpdateRequest, UserData
)
from backend.app.core.security import hash_password, decode_access_token, TokenError
from backend.app.repositories.users_repo import find_by_email, find_by_id, insert_with_defaults, update_password
from backend.app.deps.auth import get_current_user

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=True)


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
	res = await login_service(payload.email, payload.password)
	if not res["ok"]:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

	user = res["user"]
	user_data = UserData(
		id=str(user["_id"]),
		email=user["email"],
		roleKey=user.get("roleKey", "user"),
		restaurantId=user.get("restaurantId", "default"),
		locale=user.get("locale")
	)

	return TokenResponse(access_token=res["accessToken"], refresh_token=None, user=user_data)


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest):
	# Reject duplicate email
	if await find_by_email(payload.email):
		raise HTTPException(status_code=409, detail="User already exists")
	pw_hash = hash_password(payload.password)
	_ = await insert_with_defaults(payload.email, pw_hash, payload.locale)
	res = await login_service(payload.email, payload.password)
	if not res["ok"]:
		raise HTTPException(status_code=500, detail="Registration ok but login failed")

	user = res["user"]
	user_data = UserData(
		id=str(user["_id"]),
		email=user["email"],
		roleKey=user.get("roleKey", "user"),
		restaurantId=user.get("restaurantId", "default"),
		locale=user.get("locale")
	)

	return TokenResponse(access_token=res["accessToken"], refresh_token=None, user=user_data)


@router.get("/auth/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)):
	return MeResponse(
		id=str(user["_id"]),
		email=user["email"],
		roleKey=user.get("roleKey", "user"),
		locale=user.get("locale"),
	)


@router.post("/auth/forgot")
async def forgot_password(payload: ForgotPasswordRequest):
	# Return 200 regardless to avoid email enumeration
	user = await find_by_email(payload.email)
	if user:
		# create token and (in real deployment) send via email
		await pr_create(str(user["_id"]), user["email"])
	return {"ok": True}


@router.post("/auth/reset")
async def reset_password(payload: ResetPasswordRequest):
	rec = await pr_find(payload.token)
	if not rec:
		raise HTTPException(status_code=400, detail="Invalid token")
	if rec.get("used"):
		raise HTTPException(status_code=400, detail="Token already used")
	if rec.get("expiresAt") and rec["expiresAt"] < datetime.utcnow():
		raise HTTPException(status_code=400, detail="Token expired")
	uid = str(rec["userId"])
	ok = await update_password(uid, hash_password(payload.new_password))
	if not ok:
		raise HTTPException(status_code=404, detail="User not found")
	await pr_used(payload.token)
	return {"ok": True}


@router.put("/auth/locale")
async def update_locale(payload: LocaleUpdateRequest, creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
	try:
		claims = decode_access_token(creds.credentials)
	except TokenError:
		raise HTTPException(status_code=401, detail="Invalid token")
	sub = claims.get("sub")
	user = None
	try:
		user = await find_by_id(sub)
	except Exception:
		user = await find_by_email(sub)
	if not user:
		raise HTTPException(status_code=401, detail="User not found")
	from backend.app.db.mongo import get_db
	await get_db()["users"].update_one({"_id": user["_id"]}, {"$set": {"locale": payload.locale}})
	return {"ok": True}
