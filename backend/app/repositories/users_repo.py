# backend/app/repositories/users_repo.py
from __future__ import annotations
from typing import Optional, Any
from app.db.mongo import get_db


def _col():
	return get_db()["users"]


async def find_by_email(email: str) -> Optional[dict[str, Any]]:
	return await _col().find_one({"email": email})


async def insert_user(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def find_by_id(user_id: str):
	from bson import ObjectId  # runtime import to avoid hard dep if unused
	return await _col().find_one({"_id": ObjectId(user_id)})
