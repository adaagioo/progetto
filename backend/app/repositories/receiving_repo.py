# backend/app/repositories/receiving_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
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
	await _movements().insert_one({"kind": kind, "at": datetime.utcnow(), **payload})


async def create_receiving(date, items: List[Dict[str, Any]], actor_id: Optional[str] = None) -> str:
	# Persist doc first
	doc = {"date": date, "items": items, "createdAt": datetime.utcnow()}
	res = await _receiving().insert_one(doc)
	rid = res.inserted_id

	# Apply stock increments with unit alignment
	for it in items:
		inv = it.get("inventoryId")
		qty = float(it.get("quantity", 0.0))
		unit = it.get("unit")
		if not inv or qty <= 0:
			continue
		inv_id = ObjectId(inv)
		inv_doc = await _inventory().find_one({"_id": inv_id}, projection={"unit": 1})
		inv_unit = inv_doc.get("unit") if inv_doc else None
		qty_inc = qty
		if unit and inv_unit:
			qty_inc = convert_quantity(qty, unit, inv_unit)
		ok = await _inc_stock(inv_id, qty_inc)
		if ok:
			payload = {
				"inventoryId": inv_id,
				"qty": qty_inc,
				"unitCost": it.get("unitCost"),
				"supplierId": (ObjectId(it["supplierId"]) if it.get("supplierId") else None),
				"actorId": (ObjectId(actor_id) if actor_id else None),
				"receivingId": rid,
			}
			await _log("receiving", payload)
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


async def delete_receiving(rec_id: str) -> bool:
	res = await _receiving().delete_one({"_id": ObjectId(rec_id)})
	return res.deleted_count == 1


async def attach_file(rec_id: str, file_ref: Dict[str, Any]) -> bool:
	res = await _receiving().update_one(
		{"_id": ObjectId(rec_id)},
		{
			"$addToSet": {"files": {
				**file_ref,
				"attachedAt": datetime.utcnow()
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
