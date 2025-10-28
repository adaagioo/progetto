# backend/app/services/auth_service.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from app.core.config import settings
from app.repositories.users_repo import find_by_email


def _hash_verify(plain: str, hashed: bytes) -> bool:
	return bcrypt.checkpw(plain.encode("utf-8"), hashed)


def create_access_token(sub: str) -> str:
	now = datetime.now(tz=timezone.utc)
	exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
	payload = {"sub": sub, "exp": exp}
	return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


async def login(email: str, password: str) -> dict:
	user = await find_by_email(email)
	if not user:
		return {"ok": False, "reason": "INVALID_CREDENTIALS"}
	if not _hash_verify(password, user["passwordHash"]):
		return {"ok": False, "reason": "INVALID_CREDENTIALS"}
	token = create_access_token(str(user["_id"]))
	return {"ok": True, "accessToken": token, "user": user}
