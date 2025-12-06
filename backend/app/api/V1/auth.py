# backend/app/api/v1/auth.py
from __future__ import annotations

from datetime import datetime, timezone

from backend.app.repositories.password_reset_repo import pr_find, pr_create, pr_used, pr_check_rate_limit
from backend.app.repositories.login_attempts_repo import check_rate_limit as check_login_rate_limit, record_login_attempt, reset_login_attempts
from backend.app.services.auth_service import login as login_service
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.schemas.auth import (
	LoginRequest, TokenResponse, RegisterRequest, MeResponse,
	ForgotPasswordRequest, ResetPasswordRequest, LocaleUpdateRequest, UserData
)
from backend.app.core.security import hash_password, decode_access_token, TokenError
from backend.app.repositories.users_repo import find_by_email, find_by_id, insert_with_defaults, update_password
from backend.app.deps.auth import get_current_user
from backend.app.services.email_service import send_email, reset_password_email, password_changed_email
from backend.app.utils.logger import get_logger

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=True)
logger = get_logger(__name__)


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
	# Rate limiting: prevent brute force attacks (max 5 failed attempts per 15 minutes)
	rate_limited = await check_login_rate_limit(payload.email, max_failed_attempts=5, window_minutes=15)
	if rate_limited:
		logger.warning(f"Rate limit exceeded for login attempts: {payload.email}")
		raise HTTPException(
			status_code=status.HTTP_429_TOO_MANY_REQUESTS,
			detail="Too many failed login attempts. Please try again later."
		)

	# Get client IP for logging
	client_ip = request.client.host if request.client else "unknown"

	# Attempt login
	res = await login_service(payload.email, payload.password)
	if not res["ok"]:
		# Record failed attempt
		await record_login_attempt(payload.email, success=False, ip_address=client_ip)
		logger.warning(f"Failed login attempt for {payload.email} from {client_ip}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

	# Record successful attempt and reset failed attempts counter
	await record_login_attempt(payload.email, success=True, ip_address=client_ip)
	await reset_login_attempts(payload.email)
	logger.info(f"Successful login for {payload.email} from {client_ip}")

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
	# Rate limiting: prevent abuse (max 3 requests per 5 minutes per email)
	rate_limited = await pr_check_rate_limit(payload.email, max_requests=3, window_minutes=5)
	if rate_limited:
		# Return 429 Too Many Requests
		raise HTTPException(
			status_code=status.HTTP_429_TOO_MANY_REQUESTS,
			detail="Too many password reset requests. Please try again later."
		)

	# Return 200 regardless to avoid email enumeration (even if user doesn't exist)
	user = await find_by_email(payload.email)
	if user:
		# Create password reset token
		token = await pr_create(str(user["_id"]), user["email"])

		# Generate email content
		subject, plain_body, html_body = reset_password_email(
			to_email=user["email"],
			token=token,
			reset_url=None  # Uses settings.APP_URL
		)

		# Send email (non-blocking for security - no email enumeration)
		success = send_email(
			to_email=user["email"],
			subject=subject,
			body=plain_body,
			html=html_body
		)

		if not success:
			# Log warning but don't fail (security: prevent email enumeration)
			logger.warning(f"Failed to send password reset email to {user['email']}")

	return {"ok": True}


@router.post("/auth/reset")
async def reset_password(payload: ResetPasswordRequest):
	# Token validation with security logging
	rec = await pr_find(payload.token)
	if not rec:
		logger.warning(f"Password reset attempt with invalid token: {payload.token[:10]}...")
		raise HTTPException(status_code=400, detail="Invalid token")

	email = rec.get("email")  # Get email for logging

	if rec.get("used"):
		logger.warning(f"Password reset attempt with already-used token for email: {email}")
		raise HTTPException(status_code=400, detail="Token already used")

	# Handle both timezone-aware and naive datetimes
	expires_at = rec.get("expiresAt")
	if expires_at:
		now = datetime.now(tz=timezone.utc)
		# If expiresAt is naive, assume it's UTC
		if expires_at.tzinfo is None:
			expires_at = expires_at.replace(tzinfo=timezone.utc)
		if expires_at < now:
			logger.warning(f"Password reset attempt with expired token for email: {email}")
			raise HTTPException(status_code=400, detail="Token expired")

	uid = str(rec["userId"])

	ok = await update_password(uid, hash_password(payload.new_password))
	if not ok:
		logger.error(f"Failed to update password for user {uid} during password reset")
		raise HTTPException(status_code=404, detail="User not found")

	await pr_used(payload.token)
	logger.info(f"Password successfully reset for email: {email}")

	# Send confirmation email (best effort - don't block if it fails)
	if email:
		subject, plain_body, html_body = password_changed_email(to_email=email)
		success = send_email(
			to_email=email,
			subject=subject,
			body=plain_body,
			html=html_body
		)
		if not success:
			# Log warning but don't fail (password already changed successfully)
			logger.warning(f"Failed to send password change confirmation to {email}")

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
	from backend.app.repositories.users_repo import update_user
	await update_user(str(user["_id"]), {"locale": payload.locale})
	return {"ok": True}
