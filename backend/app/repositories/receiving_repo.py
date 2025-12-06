# backend/app/repositories/receiving_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.services.unit_conversion import convert_quantity


def _receiving():
	return get_db()["receiving"]


def _as_id(doc: dict) -> dict:
	"""Convert MongoDB _id to id field"""
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


def _inventory():
	return get_db()["inventory"]


def _movements():
	return get_db()["inventory_movements"]


async def _inc_stock(inv_id: ObjectId, qty: float) -> bool:
	res = await _inventory().update_one({"_id": inv_id}, {"$inc": {"quantity": float(qty)}})
	return res.matched_count == 1


async def _log(kind: str, payload: Dict[str, Any]) -> None:
	await _movements().insert_one({"kind": kind, "at": datetime.now(tz=timezone.utc), **payload})


async def insert_one(doc: Dict[str, Any]) -> str:
	# Convert date to datetime if needed (MongoDB requires datetime, not date)
	from datetime import date as date_type
	if "date" in doc and isinstance(doc["date"], date_type) and not isinstance(doc["date"], datetime):
		doc["date"] = datetime.combine(doc["date"], datetime.min.time())

	res = await _receiving().insert_one(doc)
	return str(res.inserted_id)


async def find_one(restaurant_id: str, receiving_id: str) -> Optional[Dict[str, Any]]:
	query = {"_id": ObjectId(receiving_id), "restaurantId": restaurant_id}
	return _as_id(await _receiving().find_one(query))


async def find_many(restaurant_id: str, start=None, end=None, limit: int = 200) -> List[Dict[str, Any]]:
	q: Dict[str, Any] = {"restaurantId": restaurant_id}
	if start or end:
		q["date"] = {}
		if start: q["date"]["$gte"] = start
		if end: q["date"]["$lte"] = end
	cur = _receiving().find(q).limit(limit)
	return [_as_id(doc) async for doc in cur]


async def update_one(restaurant_id: str, receiving_id: str, updates: Dict[str, Any]) -> bool:
	# Convert date to datetime if present
	if "date" in updates:
		from datetime import date as date_type
		if isinstance(updates["date"], date_type) and not isinstance(updates["date"], datetime):
			updates["date"] = datetime.combine(updates["date"], datetime.min.time())

	query = {"_id": ObjectId(receiving_id), "restaurantId": restaurant_id}
	res = await _receiving().update_one(query, {"$set": updates})
	return res.matched_count == 1


async def delete_one(restaurant_id: str, receiving_id: str) -> bool:
	query = {"_id": ObjectId(receiving_id), "restaurantId": restaurant_id}
	res = await _receiving().delete_one(query)
	return res.deleted_count == 1


async def attach_file(restaurant_id: str, receiving_id: str, file_ref: Dict[str, Any]) -> bool:
	query = {"_id": ObjectId(receiving_id), "restaurantId": restaurant_id}
	res = await _receiving().update_one(
		query,
		{
			"$addToSet": {"files": {
				**file_ref,
				"attachedAt": datetime.now(tz=timezone.utc)
			}}
		}
	)
	return res.matched_count == 1


async def detach_file(restaurant_id: str, receiving_id: str, file_id: str) -> bool:
	query = {"_id": ObjectId(receiving_id), "restaurantId": restaurant_id}
	res = await _receiving().update_one(
		query,
		{"$pull": {"files": {"fileId": file_id}}}
	)
	return res.matched_count == 1
