# backend/app/repositories/ocr_repo.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["ocr_mappings"]


async def upsert_rules(user_id: str, supplier_id: Optional[str], rules: List[Dict[str, Any]]) -> int:
	touched = 0
	for r in rules:
		key = r["key"]
		doc = {
			"userId": ObjectId(user_id),
			"supplierId": (ObjectId(supplier_id) if supplier_id else None),
			"key": key,
			"inventoryId": ObjectId(r["inventoryId"]),
			"defaultUnit": r.get("defaultUnit"),
			"updatedAt": datetime.utcnow(),
		}
		#  TODO (af): upsert by unique tuple (userId, supplierId, key).
		#   if not necessary (globally) it is necessary to remove userId as a key
		res = await _col().update_one(
			{"userId": doc["userId"], "supplierId": doc["supplierId"], "key": key},
			{"$set": doc, "$setOnInsert": {"createdAt": datetime.utcnow()}},
			upsert=True
		)
		# count as touched if modified or upserted
		if res.matched_count or (res.upserted_id is not None):
			touched += 1
	return touched


async def list_rules(user_id: str, supplier_id: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
	q: Dict[str, Any] = {"userId": ObjectId(user_id)}
	if supplier_id:
		q["supplierId"] = ObjectId(supplier_id)
	cur = _col().find(q).limit(limit)
	return [doc async for doc in cur]


async def delete_rule(user_id: str, key: str, supplier_id: Optional[str] = None) -> int:
	q: Dict[str, Any] = {"userId": ObjectId(user_id), "key": key}
	if supplier_id is not None:
		q["supplierId"] = ObjectId(supplier_id)
	else:
		q["supplierId"] = None
	res = await _col().delete_one(q)
	return res.deleted_count
