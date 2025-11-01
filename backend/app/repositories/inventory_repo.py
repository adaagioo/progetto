# backend/app/repositories/inventory_repo.py
from __future__ import annotations
from typing import Optional, Any, List
from bson import ObjectId  # type: ignore
from app.db.mongo import get_db


def _col():
	return get_db()["inventory"]


def _as_id(doc: dict) -> dict:
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def find_by_id(restaurant_id: str, inv_id: str) -> Optional[dict]:
	return _as_id(await _col().find_one({"_id": ObjectId(inv_id), "restaurantId": restaurant_id}))


async def find_all(restaurant_id: str) -> List[dict]:
	cur = _col().find({"restaurantId": restaurant_id})
	return [_as_id(d) async for d in cur]


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def delete_by_receiving(restaurant_id: str, receiving_id: str) -> int:
	res = await _col().delete_many({"restaurantId": restaurant_id, "receivingId": receiving_id})
	return res.deleted_count
