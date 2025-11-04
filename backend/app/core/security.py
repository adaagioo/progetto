# backend/app/core/security.py
from __future__ import annotations

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
