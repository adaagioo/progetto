# backend/app/repositories/receiving_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.services.unit_conversion import convert_quantity


def _receiving():
	return get_db()["receiving"]


def _inventory():
	return get_db()["inventory"]


def _movements():
	return get_db()["inventory_movements"]


async def _inc_stock(inv_id: ObjectId, qty: float) -> bool:
	res = await _inventory().update_one({"_id": inv_id}, {"$inc": {"quantity": float(qty)}})
	return res.matched_count == 1


async def _log(kind: str, payload: Dict[str, Any]) -> None:
	await _movements().insert_one({"kind": kind, "at": datetime.now(tz=timezone.utc), **payload})


async def create_receiving(date, items: List[Dict[str, Any]], actor_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
	# Convert date to datetime if needed (MongoDB requires datetime, not date)
	from datetime import date as date_type
	if isinstance(date, date_type) and not isinstance(date, datetime):
		date = datetime.combine(date, datetime.min.time())

	# Persist doc only (inventory updates handled by caller)
	doc = {"date": date, "items": items, "createdAt": datetime.now(tz=timezone.utc)}

	# Add metadata fields if provided
	if metadata:
		doc.update({k: v for k, v in metadata.items() if v is not None})

	res = await _receiving().insert_one(doc)
	rid = res.inserted_id
	return str(rid)


async def get_receiving(rec_id: str) -> Optional[Dict[str, Any]]:
	return await _receiving().find_one({"_id": ObjectId(rec_id)})


async def list_receiving(start=None, end=None, limit: int = 200) -> List[Dict[str, Any]]:
	q: Dict[str, Any] = {}
	if start or end:
		q["date"] = {}
		if start: q["date"]["$gte"] = start
		if end: q["date"]["$lte"] = end
	cur = _receiving().find(q).limit(limit)
	return [doc async for doc in cur]


async def update_receiving(rec_id: str, updates: Dict[str, Any]) -> bool:
	# Convert date to datetime if present
	if "date" in updates:
		from datetime import date as date_type
		if isinstance(updates["date"], date_type) and not isinstance(updates["date"], datetime):
			updates["date"] = datetime.combine(updates["date"], datetime.min.time())

	res = await _receiving().update_one(
		{"_id": ObjectId(rec_id)},
		{"$set": updates}
	)
	return res.matched_count == 1


async def delete_receiving(rec_id: str) -> bool:
	res = await _receiving().delete_one({"_id": ObjectId(rec_id)})
	return res.deleted_count == 1


async def attach_file(rec_id: str, file_ref: Dict[str, Any]) -> bool:
	res = await _receiving().update_one(
		{"_id": ObjectId(rec_id)},
		{
			"$addToSet": {"files": {
				**file_ref,
				"attachedAt": datetime.now(tz=timezone.utc)
			}}
		}
	)
	return res.matched_count == 1


async def detach_file(rec_id: str, file_id: str) -> bool:
	res = await _receiving().update_one(
		{"_id": ObjectId(rec_id)},
		{"$pull": {"files": {"fileId": file_id}}}
	)
	return res.matched_count == 1
