# backend/app/repositories/suppliers_repo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["suppliers"]


def _as_id(doc: dict) -> dict:
	"""Convert MongoDB _id to id field"""
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def insert_one(doc: Dict[str, Any]) -> str:
	res = await _col().insert_one({**doc})
	return str(res.inserted_id)


async def find_one(restaurant_id: str, supplier_id: str) -> Optional[Dict[str, Any]]:
	query = {"_id": ObjectId(supplier_id), "restaurantId": restaurant_id}
	return _as_id(await _col().find_one(query))


async def find_many(restaurant_id: str, limit: int = 200) -> List[Dict[str, Any]]:
	cur = _col().find({"restaurantId": restaurant_id}).limit(limit)
	return [_as_id(doc) async for doc in cur]


async def update_one(restaurant_id: str, supplier_id: str, patch: Dict[str, Any]) -> bool:
	query = {"_id": ObjectId(supplier_id), "restaurantId": restaurant_id}
	res = await _col().update_one(query, {"$set": patch})
	return res.matched_count == 1


async def delete_one(restaurant_id: str, supplier_id: str) -> bool:
	query = {"_id": ObjectId(supplier_id), "restaurantId": restaurant_id}
	res = await _col().delete_one(query)
	return res.deleted_count == 1


async def attach_file(restaurant_id: str, supplier_id: str, file_ref: Dict[str, Any]) -> bool:
	query = {"_id": ObjectId(supplier_id), "restaurantId": restaurant_id}
	res = await _col().update_one(
		query,
		{
			"$addToSet": {"files": {
				**file_ref,
				"attachedAt": datetime.now(tz=timezone.utc)
			}}
		}
	)
	return res.matched_count == 1


async def detach_file(restaurant_id: str, supplier_id: str, file_id: str) -> bool:
	query = {"_id": ObjectId(supplier_id), "restaurantId": restaurant_id}
	res = await _col().update_one(
		query,
		{"$pull": {"files": {"fileId": file_id}}}
	)
	return res.matched_count == 1
