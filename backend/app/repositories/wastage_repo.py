# backend/app/repositories/wastage_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["wastage"]


def _as_id(doc: dict) -> dict:
	"""Convert MongoDB _id to id field"""
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def find_one(restaurant_id: str, wastage_id: str) -> Optional[Dict[str, Any]]:
	query = {"_id": ObjectId(wastage_id), "restaurantId": restaurant_id}
	return _as_id(await _col().find_one(query))


async def find_many(restaurant_id: str, start: Optional[date] = None, end: Optional[date] = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
	q: Dict[str, Any] = {"restaurantId": restaurant_id}
	if start and end:
		q["date"] = {"$gte": start, "$lte": end}
	cur = _col().find(q, limit=limit, skip=skip).sort([("date", 1)])
	return [_as_id(d) async for d in cur]


async def delete_one(restaurant_id: str, wastage_id: str) -> bool:
	query = {"_id": ObjectId(wastage_id), "restaurantId": restaurant_id}
	res = await _col().delete_one(query)
	return res.deleted_count == 1
