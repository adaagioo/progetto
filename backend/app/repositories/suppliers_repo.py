# backend/app/repositories/suppliers_repo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["suppliers"]


async def create(data: Dict[str, Any]) -> str:
	res = await _col().insert_one({**data})
	return str(res.inserted_id)


async def get_by_id(supplier_id: str) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"_id": ObjectId(supplier_id)})


async def update(supplier_id: str, patch: Dict[str, Any]) -> bool:
	res = await _col().update_one({"_id": ObjectId(supplier_id)}, {"$set": patch})
	return res.matched_count == 1


async def delete(supplier_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(supplier_id)})
	return res.deleted_count == 1


async def list_all(limit: int = 200) -> List[Dict[str, Any]]:
	cur = _col().find({}).limit(limit)
	return [doc async for doc in cur]


async def attach_file(supplier_id: str, file_ref: Dict[str, Any]) -> bool:
	res = await _col().update_one(
		{"_id": ObjectId(supplier_id)},
		{
			"$addToSet": {"files": {
				**file_ref,
				"attachedAt": datetime.now(tz=timezone.utc)
			}}
		}
	)
	return res.matched_count == 1


async def detach_file(supplier_id: str, file_id: str) -> bool:
	res = await _col().update_one(
		{"_id": ObjectId(supplier_id)},
		{"$pull": {"files": {"fileId": file_id}}}
	)
	return res.matched_count == 1
