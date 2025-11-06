from __future__ import annotations
from typing import Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db


def _recipes(): return get_db()["recipes"]


def _inventory(): return get_db()["inventory"]


async def populate_menu_item_data(item: Dict[str, Any]) -> Dict[str, Any]:
	rid = item.get("recipeId")
	qty = float(item.get("quantity", 1.0))
	if not rid:
		return {**item, "recipeName": None, "canPrepare": False, "maxServings": 0}
	r = await _recipes().find_one({"_id": ObjectId(rid)}, projection={"name": 1, "ingredients": 1})
	if not r:
		return {**item, "recipeName": None, "canPrepare": False, "maxServings": 0}
	name = r.get("name")
	max_servings = float("inf")
	for ing in (r.get("ingredients") or []):
		inv = ing.get("inventoryId")
		q = float(ing.get("quantity", 0.0))
		if not inv or q <= 0:
			continue
		inv_doc = await _inventory().find_one({"_id": ObjectId(inv)}, projection={"quantity": 1})
		on_hand = float(inv_doc.get("quantity", 0.0)) if inv_doc else 0.0
		max_servings = min(max_servings, on_hand / q if q else 0.0)
	if max_servings == float("inf"):
		max_servings = 0.0
	can_prepare = max_servings >= qty if qty > 0 else False
	return {**item, "recipeName": name, "canPrepare": bool(can_prepare),
	        "maxServings": max(0.0, round(max_servings, 4))}
