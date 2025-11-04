# backend/app/repositories/recipes_repo.py
from __future__ import annotations
from typing import Optional, List
from bson import ObjectId  # type: ignore
from backend.app.db.mongo import get_db


def _col():
	return get_db()["recipes"]


def _as_id(doc: dict) -> dict:
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def find_one(restaurant_id: str, recipe_id: str) -> Optional[dict]:
	return _as_id(await _col().find_one({"_id": ObjectId(recipe_id), "restaurantId": restaurant_id}))


async def find_many(restaurant_id: str) -> List[dict]:
	cur = _col().find({"restaurantId": restaurant_id})
	return [_as_id(d) async for d in cur]


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def update_one(restaurant_id: str, recipe_id: str, patch: dict) -> bool:
	res = await _col().update_one({"_id": ObjectId(recipe_id), "restaurantId": restaurant_id}, {"$set": patch})
	return res.modified_count > 0


async def delete_one(restaurant_id: str, recipe_id: str) -> bool:
	res = await _col().delete_one({"_id": ObjectId(recipe_id), "restaurantId": restaurant_id})
	return res.deleted_count > 0


async def lookup_recipe_dependencies(recipe_id: str) -> dict:
	from bson import ObjectId
	db = get_db()
	rid = ObjectId(recipe_id)

	names = await db.list_collection_names()
	used_in_menus = await db.get_collection("menus").count_documents({"items.recipeId": rid}) if "menus" in names else 0
	used_in_preplist = await db.get_collection("preplists").count_documents(
		{"tasks.recipeId": rid}) if "preplists" in names else 0
	used_in_orderlist = await db.get_collection("orderlists").count_documents(
		{"items.recipeId": rid}) if "orderlists" in names else 0

	return {
		"recipeId": recipe_id,
		"usedInMenus": int(used_in_menus),
		"usedInPrepList": int(used_in_preplist),
		"usedInOrderList": int(used_in_orderlist),
		"preparationRefs": 0,
		"preparationIds": [],
	}
