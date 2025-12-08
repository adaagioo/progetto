# backend/app/deps/auth.py
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.security import decode_access_token, TokenError
from backend.app.repositories.users_repo import find_by_email, find_by_id
from typing import Any, Dict

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Dict[str, Any]:
	"""Validate JWT and load the current user from DB.
	Returns a dict-like user (as stored in Mongo).
	"""
	try:
		token = credentials.credentials
		claims = decode_access_token(token)
		sub = claims.get("sub")

		# Try by id first; fallback by email if needed.
		user = None
		try:
			from bson import ObjectId
			from bson.errors import InvalidId
			# Only attempt ObjectId lookup if sub looks like a valid ObjectId
			if ObjectId.is_valid(sub):
				user = await find_by_id(str(sub))
		except InvalidId:
			# Invalid ObjectId format, will try email lookup below
			pass
		except Exception as e:
			# Database or unexpected error - log and raise
			import logging
			logging.error(f"Error looking up user by ID {sub}: {e}")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Database error during authentication"
			)

		if not user:
			user = await find_by_email(str(sub))

		if not user:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="User not found or inactive"
			)

		return user

	except TokenError as e:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=str(e)
		)
	except HTTPException:
		raise
	except Exception as e:
		# Log unexpected errors for debugging
		import logging
		logging.error(f"Unexpected error in get_current_user: {e}", exc_info=True)
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Authentication failed"
		)
