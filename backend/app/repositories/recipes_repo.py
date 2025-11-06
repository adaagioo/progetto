# backend/app/repositories/recipes_repo.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
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


async def count_sales_refs(recipe_id: str) -> int:
	s = _sales()
	if s is None:
		return 0
	rid = ObjectId(recipe_id)
	return await s.count_documents({"items.recipeId": rid})


async def lookup_recipe_dependencies(recipe_id: str) -> Dict[str, Any]:
	rid = ObjectId(recipe_id)
	menus = _menus()
	prepl = _preplist()
	ordl = _orderlist()
	used_in_menus = await menus.count_documents({"items.recipeId": rid}) if menus is not None else 0
	used_in_preplist = await prepl.count_documents({"tasks.recipeId": rid}) if prepl is not None else 0
	used_in_orderlist = await ordl.count_documents({"items.recipeId": rid}) if ordl is not None else 0
	sales_refs = await count_sales_refs(recipe_id)
	return {
		"recipeId": recipe_id,
		"usedInMenus": int(used_in_menus),
		"usedInPrepList": int(used_in_preplist),
		"usedInOrderList": int(used_in_orderlist),
		"salesRefs": int(sales_refs),
		"preparationRefs": 0,
		"preparationIds": [],
	}


def _sales():
	return get_db().get_collection("sales")


def _menus():
	return get_db().get_collection("menus")


def _preplist():
	return get_db().get_collection("preplists")


def _orderlist():
	return get_db().get_collection("orderlists")
