# backend/app/repositories/users_repo.py
from __future__ import annotations
from typing import Optional, Any, List

from bson import ObjectId

from backend.app.db.mongo import get_db


def _col():
	return get_db()["users"]


def _oid(s: str):
	try:
		return ObjectId(s)
	except Exception:
		return s


async def find_by_email(email: str) -> Optional[dict[str, Any]]:
	return await _col().find_one({"email": email})


async def insert_user(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def find_by_id(user_id: str):
	return await _col().find_one({"_id": ObjectId(user_id)})


async def list_users(limit: int = 50, skip: int = 0) -> List[dict]:
	cursor = _col().find({}, limit=limit, skip=skip).sort([("_id", 1)])
	return [doc async for doc in cursor]


async def delete_user(user_id: str) -> bool:
	from bson import ObjectId
	res = await _col().delete_one({"_id": ObjectId(user_id)})
	return res.deleted_count == 1


async def insert_with_defaults(email: str, password_hash: str, locale: str | None = None) -> str:
	doc = {
		"email": email,
		"password": password_hash,
		"roleKey": "admin",  # Changed from "owner" - frontend only shows UI for admin/manager
		"locale": locale,
		"restaurantId": "default",
	}
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def update_password(user_id: str, password_hash: str) -> bool:
	from bson import ObjectId
	res = await _col().update_one({"_id": ObjectId(user_id)}, {"$set": {"password": password_hash}})
	return res.matched_count == 1


async def create_user(email: str, password_hash: str, role_key: str = "user", locale: str | None = None, display_name: str | None = None) -> str:
	doc = {
		"email": email,
		"password": password_hash,
		"roleKey": role_key,
		"locale": locale,
		"restaurantId": "default",
		"displayName": display_name,
		"isDisabled": False,
	}
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def update_user(user_id: str, patch: dict) -> bool:
	from bson import ObjectId
	allowed = {k: v for k, v in patch.items() if k in {"email", "roleKey", "locale", "restaurantId", "displayName", "isDisabled"}}
	if not allowed:
		return True
	res = await _col().update_one({"_id": ObjectId(user_id)}, {"$set": allowed})
	return res.matched_count == 1
