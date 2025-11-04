# backend/app/repositories/password_reset_repo.py
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from secrets import token_urlsafe
from bson import ObjectId
from backend.app.db.mongo import get_db

COLLECTION = "password_resets"
TTL_HOURS = 2


def _col():
	return get_db()[COLLECTION]


async def create_token(user_id: str, email: str) -> str:
	tok = token_urlsafe(32)
	doc = {
		"token": tok,
		"userId": ObjectId(user_id),
		"email": email,
		"createdAt": datetime.utcnow(),
		"expiresAt": datetime.utcnow() + timedelta(hours=TTL_HOURS),
		"used": False,
	}
	await _col().insert_one(doc)
	return tok


async def find_by_token(token: str) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"token": token})


async def mark_used(token: str) -> None:
	await _col().update_one({"token": token}, {"$set": {"used": True, "usedAt": datetime.utcnow()}})
