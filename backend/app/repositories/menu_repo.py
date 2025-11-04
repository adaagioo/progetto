# backend/app/repositories/menu_repo.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["menus"]


async def get_by_date(d) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"date": d})


async def create_menu(d, items: List[dict]) -> str:
	res = await _col().insert_one({"date": d, "items": items})
	return str(res.inserted_id)


async def update_menu(menu_id: str, items: List[dict]) -> bool:
	res = await _col().update_one({"_id": ObjectId(menu_id)}, {"$set": {"items": items}})
	return res.matched_count == 1


async def get_menu(menu_id: str) -> Optional[Dict[str, Any]]:
	return await _col().find_one({"_id": ObjectId(menu_id)})


async def delete_menu(menu_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(menu_id)})
	return res.deleted_count == 1


async def list_menus(start=None, end=None, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
	q: Dict[str, Any] = {}
	if start and end:
		q["date"] = {"$gte": start, "$lte": end}
	cur = _col().find(q, limit=limit, skip=skip).sort([("date", 1)])
	return [d async for d in cur]
