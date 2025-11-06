# backend/app/repositories/wastage_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["wastage"]


async def create_wastage(d: date, items: List[dict]) -> str:
	res = await _col().insert_one({"date": d, "items": items, "createdAt": datetime.utcnow()})
	return str(res.inserted_id)


async def get_wastage(w_id: str) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"_id": ObjectId(w_id)})


async def list_wastage(start: Optional[date] = None, end: Optional[date] = None, limit: int = 100, skip: int = 0) -> \
		List[Dict[str, Any]]:
	q: Dict[str, Any] = {}
	if start and end:
		q["date"] = {"$gte": start, "$lte": end}
	cur = _col().find(q, limit=limit, skip=skip).sort([("date", 1)])
	return [d async for d in cur]


async def delete_wastage(w_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(w_id)})
	return res.deleted_count == 1
