# backend/app/services/order_list_service.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.services.unit_conversion import convert_quantity


def _menus(): return get_db()["menus"]


def _recipes(): return get_db()["recipes"]


def _inventory(): return get_db()["inventory"]


async def _load_menu(for_date: date) -> Dict[str, Any] | None:
	return await _menus().find_one({"date": for_date})


async def _load_inventory_map() -> Dict[str, Dict[str, Any]]:
	m: Dict[str, Dict[str, Any]] = {}
	async for it in _inventory().find({}, projection={"_id": 1, "name": 1, "quantity": 1, "unit": 1}):
		m[str(it["_id"])] = {
			"name": it.get("name") or str(it["_id"]),
			"onHand": float(it.get("quantity", 0.0)),
			"unit": it.get("unit"),
		}
	return m


async def compute_order_list(for_date: date) -> Dict[str, Any]:
	"""Aggregate inventory items needed from the day's menu.
	Assumptions:
	  - Recipe ingredients referencing inventoryId contribute to required quantity.
	  - We aggregate required per inventoryId and subtract on-hand quantity (not lower than 0).
	"""
	menu = await _load_menu(for_date)
	if not menu or not menu.get("items"):
		return {"date": for_date, "items": []}
	recipe_ids = [ObjectId(i["recipeId"]) for i in menu["items"] if i.get("recipeId")]
	qty_by_recipe = {str(ObjectId(i["recipeId"])): float(i.get("quantity", 1.0)) for i in menu["items"] if
	                 i.get("recipeId")}
	inv_map = await _load_inventory_map()
	need_by_inv: Dict[str, float] = {}
	async for r in _recipes().find({"_id": {"$in": recipe_ids}}, projection={"ingredients": 1}):
		rid = str(r["_id"])
		recipe_mult = qty_by_recipe.get(rid, 1.0)
		for ing in (r.get("ingredients") or []):
			inv = ing.get("inventoryId")
			if not inv:
				continue
			qty = float(ing.get("quantity", 0.0)) * recipe_mult
			inv_key = str(inv)
			inv_unit = inv_map.get(inv_key, {}).get("unit")
			ing_unit = ing.get("unit")
			if inv_unit and ing_unit:
				qty = convert_quantity(qty, ing_unit, inv_unit)
			need_by_inv[inv_key] = need_by_inv.get(inv_key, 0.0) + qty
	inv_map = await _load_inventory_map()
	items: List[Dict[str, Any]] = []
	for inv_id, required in need_by_inv.items():
		meta = inv_map.get(inv_id, {"name": inv_id, "onHand": 0.0, "unit": None})
		inv_unit = meta.get("unit")

		# Convert required to inventory unit if possible
		req_in_inv_unit = required
		# TODO (af):
		# We don't have ingredient unit here (aggregated), assume ingredient units already match recipe units.
		# For robustness, if inv_unit is known and ingredients had units, you'd convert per-ingredient before summing.
		on_hand = float(meta.get("onHand", 0.0))

		# Net needed to fulfill today's menu
		net_needed = max(0.0, req_in_inv_unit - on_hand)

		# Reorder policy
		reorder_level = float(meta.get("reorderLevel", 0.0)) if meta.get("reorderLevel") is not None else None
		target_level = float(meta.get("targetLevel", 0.0)) if meta.get("targetLevel") is not None else None
		reorder_qty = 0.0

		if reorder_level is not None and target_level is not None and on_hand < reorder_level:
			reorder_qty = max(0.0, target_level - on_hand)
		order_qty = max(net_needed, reorder_qty)

		if order_qty <= 0:
			continue
		items.append({
			"inventoryId": inv_id,
			"name": meta["name"],
			"quantity": round(order_qty, 4),
			"unit": inv_unit,
			"supplierId": meta.get("defaultSupplierId"),
		})
	items.sort(key=lambda x: x["name"])
	return {"date": for_date, "items": items}
