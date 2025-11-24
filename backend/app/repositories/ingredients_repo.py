# backend/app/repositories/ingredients_repo.py
from __future__ import annotations
from typing import Optional, Any, List
from bson import ObjectId  # type: ignore
from backend.app.db.mongo import get_db


def _col():
	return get_db()["ingredients"]


def _as_id(doc: dict) -> dict:
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def find_one(restaurant_id: str, ingredient_id: str) -> Optional[dict]:
	return _as_id(await _col().find_one({"_id": ObjectId(ingredient_id), "restaurantId": restaurant_id}))


async def find_many(restaurant_id: str) -> List[dict]:
	cur = _col().find({"restaurantId": restaurant_id})
	return [_as_id(d) async for d in cur]


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def update_one(restaurant_id: str, ingredient_id: str, patch: dict) -> bool:
	res = await _col().update_one({"_id": ObjectId(ingredient_id), "restaurantId": restaurant_id}, {"$set": patch})
	return res.modified_count > 0


async def delete_one(restaurant_id: str, ingredient_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(ingredient_id), "restaurantId": restaurant_id})
	return res.deleted_count > 0
