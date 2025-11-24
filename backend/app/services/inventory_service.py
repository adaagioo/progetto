from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from bson import ObjectId
from datetime import datetime, timezone
from backend.app.db.mongo import get_db
from backend.app.repositories.inventory_repo import find_all, find_by_id, insert_one, delete_by_receiving
from backend.app.services.unit_conversion import convert_quantity


def _recipes(): return get_db()["recipes"]


def _inventory(): return get_db()["inventory"]


def _movements(): return get_db()["inventory_movements"]


async def list_inventory(restaurant_id: str) -> List[dict]:
	return await find_all(restaurant_id)


async def get_inventory(restaurant_id: str, inv_id: str) -> Optional[dict]:
	return await find_by_id(restaurant_id, inv_id)


async def create_inventory(doc: dict) -> str:
	return await insert_one(doc)


async def delete_inventory_by_receiving(restaurant_id: str, receiving_id: str) -> int:
	return await delete_by_receiving(restaurant_id, receiving_id)


async def _dec(inv_id: ObjectId, qty: float) -> bool:
	res = await _inventory().update_one({"_id": inv_id}, {"$inc": {"quantity": -abs(float(qty))}})
	return res.matched_count == 1


async def log_movement(kind: str, payload: Dict[str, Any]) -> None:
	doc = {"kind": kind, "at": datetime.now(tz=timezone.utc), **payload}
	await _movements().insert_one(doc)


async def deduct_stock_for_recipe(recipe_id: str, servings: float, actor_id: str | None = None) -> Tuple[
	bool, List[Dict[str, Any]]]:
	r = await _recipes().find_one({"_id": ObjectId(recipe_id)}, projection={"ingredients": 1, "name": 1})
	if not r:
		return False, []
	ing_list = r.get("ingredients") or []
	movements: List[Dict[str, Any]] = []
	for ing in ing_list:
		inv = ing.get("inventoryId")
		if not inv:
			continue
		inv_id = ObjectId(inv)
		qty = float(ing.get("quantity", 0.0)) * float(servings)
		unit = ing.get("unit")
		inv_doc = await _inventory().find_one({"_id": inv_id}, projection={"unit": 1})
		inv_unit = inv_doc.get("unit") if inv_doc else None
		if unit and inv_unit:
			qty = convert_quantity(qty, unit, inv_unit)
		ok = await _dec(inv_id, qty)
		if ok:
			m = {"inventoryId": inv_id, "qty": qty, "recipeId": ObjectId(recipe_id),
			     "actorId": (ObjectId(actor_id) if actor_id else None)}
			await log_movement("recipe-consume", m)
			m["inventoryId"] = str(inv_id)
			m["recipeId"] = str(m["recipeId"])
			if m["actorId"]:
				m["actorId"] = str(m["actorId"])
			movements.append(m)
	return True, movements


async def deduct_stock_for_wastage(items: List[Dict[str, Any]], actor_id: str | None = None) -> Tuple[
	bool, List[Dict[str, Any]]]:
	movements: List[Dict[str, Any]] = []
	for it in items:
		inv_id = ObjectId(it["inventoryId"])
		qty = float(it.get("quantity", 0.0))
		unit = it.get("unit")
		inv_doc = await _inventory().find_one({"_id": inv_id}, projection={"unit": 1})
		inv_unit = inv_doc.get("unit") if inv_doc else None
		if unit and inv_unit:
			qty = convert_quantity(qty, unit, inv_unit)
		ok = await _dec(inv_id, qty)
		if ok:
			m = {"inventoryId": inv_id, "qty": qty, "reason": it.get("reason"),
			     "actorId": (ObjectId(actor_id) if actor_id else None)}
			await log_movement("wastage", m)
			m["inventoryId"] = str(inv_id)
			if m["actorId"]:
				m["actorId"] = str(m["actorId"])
			movements.append(m)
	return True, movements
