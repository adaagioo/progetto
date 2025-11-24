# backend/app/core/security.py
from __future__ import annotations

import base64, hashlib, hmac, secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import jwt
from fastapi import HTTPException, status
from backend.app.core.config import settings

ALGORITHM = "HS256"


class TokenError(HTTPException):
	def __init__(self, detail: str = "Invalid authentication credentials"):
		super().__init__(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=detail,
			headers={"WWW-Authenticate": "Bearer"},
		)


def decode_access_token(token: str) -> Dict[str, Any]:
	try:
		payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
	except jwt.ExpiredSignatureError:
		raise TokenError("Token expired")
	except jwt.InvalidTokenError:
		raise TokenError("Invalid token")
	# Basic claims validation
	sub = payload.get("sub")
	if not sub:
		raise TokenError("Missing subject in token")
	# Optional: 'exp' is validated by jwt.decode
	return payload


_PBKDF2_ITERS = 130_000
_SALT_LEN = 16


def hash_password(password: str) -> str:
	if password is None:
		raise ValueError("password is None")
	salt = secrets.token_bytes(_SALT_LEN)
	dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERS)
	return f"pbkdf2_sha256${_PBKDF2_ITERS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
	try:
		algo, iters_s, salt_b64, hash_b64 = stored.split("$", 3)
		if algo != "pbkdf2_sha256":
			return False
		iters = int(iters_s)
		salt = base64.b64decode(salt_b64)
		expected = base64.b64decode(hash_b64)
		dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
		return hmac.compare_digest(dk, expected)
	except Exception:
		return False
