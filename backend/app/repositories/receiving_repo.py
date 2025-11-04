# backend/app/repositories/receiving_repo.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["receivings"]


async def create_receiving(supplier_id: str, date, items: List[dict]) -> str:
	doc = {
		"supplierId": ObjectId(supplier_id),
		"date": date,
		"items": items,
		"files": [],
		"createdAt": datetime.now(tz=timezone.utc),
	}
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def get_receiving(rec_id: str) -> Optional[Dict[str, Any]]:
	doc = await _col().find_one({"_id": ObjectId(rec_id)})
	return doc


async def list_receivings(limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
	cur = _col().find({}, limit=limit, skip=skip).sort([("_id", -1)])
	return [d async for d in cur]


async def attach_file(rec_id: str, file_id: str):
	await _col().update_one({"_id": ObjectId(rec_id)}, {"$addToSet": {"files": ObjectId(file_id)}})


async def list_files(rec_id: str) -> List[str]:
	doc = await _col().find_one({"_id": ObjectId(rec_id)}, projection={"files": 1})
	if not doc:
		return []
	return [str(fid) for fid in doc.get("files", [])]
