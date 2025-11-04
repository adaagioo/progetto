# backend/app/repositories/suppliers_repo.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["suppliers"]


async def create_supplier(payload: Dict[str, Any]) -> str:
	res = await _col().insert_one(payload)
	return str(res.inserted_id)


async def get_supplier(supplier_id: str) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"_id": ObjectId(supplier_id)})


async def list_suppliers(limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
	cur = _col().find({}, limit=limit, skip=skip).sort([("name", 1)])
	return [d async for d in cur]


async def update_supplier(supplier_id: str, patch: Dict[str, Any]) -> bool:
	res = await _col().update_one({"_id": ObjectId(supplier_id)}, {"$set": patch})
	return res.matched_count == 1


async def delete_supplier(supplier_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(supplier_id)})
	return res.deleted_count == 1
