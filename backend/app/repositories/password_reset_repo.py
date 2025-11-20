# backend/app/repositories/password_reset_repo.py
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from bson import ObjectId
from backend.app.db.mongo import get_db

_COLLECTION = "password_resets"
TTL_HOURS = 2


async def _col():
	return get_db()[_COLLECTION]


async def _ensure_indexes():
	col = await _col()
	try:
		await col.create_index("token", unique=True)
	except Exception:
		pass
	try:
		await col.create_index("expiresAt", expireAfterSeconds=0)
	except Exception:
		pass


def _to_object_id(maybe_id: str):
	try:
		return ObjectId(maybe_id)
	except Exception:
		return maybe_id


async def pr_create(user_id: str, email: str, ttl_minutes: int = 30) -> str:
	await _ensure_indexes()
	col = await _col()
	token = token_urlsafe(32)
	now = datetime.now(tz=timezone.utc)
	doc = {
		"token": token,
		"userId": _to_object_id(user_id),
		"email": email,
		"createdAt": now,
		"expiresAt": now + timedelta(minutes=ttl_minutes),
		"used": False,
		"usedAt": None,
	}
	await col.insert_one(doc)
	return token


async def pr_find(token: str) -> Optional[Dict[str, Any]]:
	col = await _col()
	return await col.find_one({"token": token})


async def pr_used(token: str) -> bool:
	col = await _col()
	res = await col.update_one({"token": token}, {"$set": {"used": True, "usedAt": datetime.now(tz=timezone.utc)}})
	return res.matched_count == 1
