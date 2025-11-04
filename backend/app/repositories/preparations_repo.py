# backend/app/repositories/preparations_repo.py
from __future__ import annotations
from typing import Optional, List
from bson import ObjectId  # type: ignore
from backend.app.db.mongo import get_db


def _col():
	return get_db()["preparations"]


def _as_id(doc: dict) -> dict:
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def find_one(restaurant_id: str, prep_id: str) -> Optional[dict]:
	return _as_id(await _col().find_one({"_id": ObjectId(prep_id), "restaurantId": restaurant_id}))


async def find_many(restaurant_id: str) -> List[dict]:
	cur = _col().find({"restaurantId": restaurant_id})
	return [_as_id(d) async for d in cur]


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def update_one(restaurant_id: str, prep_id: str, patch: dict) -> bool:
	res = await _col().update_one({"_id": ObjectId(prep_id), "restaurantId": restaurant_id}, {"$set": patch})
	return res.modified_count > 0


async def delete_one(restaurant_id: str, prep_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(prep_id), "restaurantId": restaurant_id})
	return res.deleted_count > 0


async def lookup_preparation_dependencies(prep_id: str) -> dict:
	from bson import ObjectId
	db = get_db()
	pid = ObjectId(prep_id)

	cursor = db.get_collection("recipes").find({
		"$or": [
			{"components.preparationId": pid},
			{"ingredients.preparationId": pid},
		]
	}, projection={"_id": 1})
	r_ids = [str(d["_id"]) async for d in cursor]

	return {
		"preparationId": prep_id,
		"recipesUsing": len(r_ids),
		"recipeIds": r_ids,
	}
