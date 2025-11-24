# backend/app/repositories/movements_repo.py
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
from bson import ObjectId
from backend.app.db.mongo import get_db


def _movements():
	return get_db()["inventory_movements"]


async def find_receiving_price_history(inventory_id: str, limit: int = 200) -> List[Dict[str, Any]]:
	inv = ObjectId(inventory_id)
	cur = _movements().find({
		"kind": "receiving",
		"inventoryId": inv
	}, {
		"at": 1,
		"unitCost": 1,
		"receivingId": 1,
		"_id": 0
	}).sort("at", -1).limit(limit)
	return [doc async for doc in cur]
