from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from bson import ObjectId
from datetime import datetime, timezone, date, timedelta
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


async def get_expiring_inventory_buckets(restaurant_id: str, days: int = 3) -> Dict[str, Any]:
	"""
	Get count of items expiring within specified days, bucketed by day.

	Args:
		restaurant_id: Restaurant ID to filter by
		days: Number of days to bucket (1-30)

	Returns:
		Dict with 'buckets' (day1, day2, ...) and 'total' count
	"""
	# Validate days parameter
	if days < 1 or days > 30:
		raise ValueError("Days must be between 1 and 30")

	# Fetch inventory items with expiry dates
	inventory_items = await _inventory().find({
		"restaurantId": restaurant_id,
		"expiryDate": {"$exists": True, "$ne": None}
	}).to_list(10000)

	today = date.today()
	buckets = {f"day{i}": 0 for i in range(1, days + 1)}

	for item in inventory_items:
		expiry_str = item.get("expiryDate")
		if not expiry_str:
			continue

		try:
			if isinstance(expiry_str, str):
				expiry_date = date.fromisoformat(expiry_str.split('T')[0])
			elif isinstance(expiry_str, datetime):
				expiry_date = expiry_str.date()
			else:
				continue

			days_until_expiry = (expiry_date - today).days

			# Bucket items by days (1, 2, 3, etc.)
			if 0 <= days_until_expiry < days:
				bucket_key = f"day{days_until_expiry + 1}"
				if bucket_key in buckets:
					buckets[bucket_key] += 1

		except (ValueError, AttributeError):
			continue

	return {"buckets": buckets, "total": sum(buckets.values())}


async def _dec(inv_id: ObjectId, qty_val: float) -> bool:
	"""Decrement inventory quantity. Returns False if insufficient stock."""
	qty_abs = abs(float(qty_val))
	# Only decrement if quantity is sufficient (atomic check-and-set)
	# Note: inventory documents use 'qty' field, not 'quantity'
	res = await _inventory().update_one(
		{"_id": inv_id, "qty": {"$gte": qty_abs}},
		{"$inc": {"qty": -qty_abs}}
	)
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
		if not ok:
			# Stock deduction failed - either inventory not found or insufficient quantity
			raise ValueError(f"Insufficient stock for inventory {inv_id} (recipe: {r.get('name', recipe_id)})")
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
		item_id_str = it.get("inventoryId") or it.get("itemId")
		qty = float(it.get("quantity", 0.0))
		unit = it.get("unit")

		# Try to find inventory - first by _id, then by ingredientId
		inv_doc = None
		inv_id = None
		try:
			inv_id = ObjectId(item_id_str)
			inv_doc = await _inventory().find_one({"_id": inv_id}, projection={"unit": 1, "qty": 1})
		except Exception:
			pass

		# If not found by _id, try by ingredientId (frontend may send ingredient ID)
		if not inv_doc:
			inv_doc = await _inventory().find_one(
				{"ingredientId": item_id_str},
				projection={"_id": 1, "unit": 1, "qty": 1}
			)
			if inv_doc:
				inv_id = inv_doc["_id"]

		if not inv_doc or not inv_id:
			raise ValueError(f"No inventory found for item {item_id_str}")

		inv_unit = inv_doc.get("unit")
		if unit and inv_unit:
			qty = convert_quantity(qty, unit, inv_unit)
		ok = await _dec(inv_id, qty)
		if not ok:
			# Stock deduction failed - insufficient quantity
			raise ValueError(f"Insufficient stock for inventory {inv_id} (wastage)")
		m = {"inventoryId": inv_id, "qty": qty, "reason": it.get("reason"),
		     "actorId": (ObjectId(actor_id) if actor_id else None)}
		await log_movement("wastage", m)
		m["inventoryId"] = str(inv_id)
		if m["actorId"]:
			m["actorId"] = str(m["actorId"])
		movements.append(m)
	return True, movements
