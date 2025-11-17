# backend/app/services/prep_list_service.py
from __future__ import annotations
from datetime import date
from typing import Dict, Any, List, Tuple
from bson import ObjectId
from backend.app.db.mongo import get_db


def _menus(): return get_db()["menus"]


def _recipes(): return get_db()["recipes"]


def _preps(): return get_db()["preparations"]


async def _load_menu(for_date: date) -> Dict[str, Any] | None:
	# MongoDB stores dates as strings in ISO format, so convert for query
	date_str = for_date.isoformat()
	return await _menus().find_one({"date": date_str})


async def _map_preparation_names(ids: List[ObjectId]) -> Dict[str, str]:
	names: Dict[str, str] = {}
	if not ids:
		return names
	async for p in _preps().find({"_id": {"$in": ids}}, projection={"name": 1}):
		names[str(p["_id"])] = p.get("name") or str(p["_id"])
	return names


async def compute_prep_list(for_date: date) -> Dict[str, Any]:
	"""Aggregate preparation tasks from the day's menu.
	Assumptions:
	  - Menu: { date, items: [{ recipeId, quantity }] }
	  - Recipe: has ingredients[] where each ingredient may have preparationId, quantity, unit, name
	We aggregate tasks by preparationId (fallback by ingredient name).
	"""
	menu = await _load_menu(for_date)
	if not menu or not menu.get("items"):
		return {"date": for_date, "tasks": []}
	# Collect all recipe ids
	recipe_ids = [ObjectId(i["recipeId"]) for i in menu["items"] if i.get("recipeId")]
	qty_by_recipe = {str(ObjectId(i["recipeId"])): float(i.get("quantity", 1.0)) for i in menu["items"] if
	                 i.get("recipeId")}
	# Load recipes in one query
	tasks_by_key: Dict[str, Dict[str, Any]] = {}
	async for r in _recipes().find({"_id": {"$in": recipe_ids}}, projection={"ingredients": 1, "name": 1}):
		rid = str(r["_id"])
		recipe_mult = qty_by_recipe.get(rid, 1.0)
		for ing in (r.get("ingredients") or []):
			prep_id = ing.get("preparationId")
			name = ing.get("name") or "Unnamed"
			qty = float(ing.get("quantity", 0.0)) * recipe_mult
			unit = ing.get("unit")
			key = f"prep:{prep_id}" if prep_id else f"name:{name}:{unit or ''}"
			t = tasks_by_key.setdefault(key, {"preparationId": prep_id, "recipeId": None, "name": name, "quantity": 0.0,
			                                  "unit": unit})
			t["quantity"] += qty
	# Resolve preparation names
	prep_ids = [ObjectId(t["preparationId"]) for t in tasks_by_key.values() if t.get("preparationId")]
	name_map = await _map_preparation_names(prep_ids)
	tasks: List[Dict[str, Any]] = []
	for t in tasks_by_key.values():
		if t.get("preparationId"):
			t["name"] = name_map.get(str(ObjectId(t["preparationId"])), t["name"])
		tasks.append({
			"preparationId": t.get("preparationId"),
			"recipeId": t.get("recipeId"),
			"name": t["name"],
			"quantity": round(float(t["quantity"]), 4),
			"unit": t.get("unit"),
		})
	# Sort by name for stable output
	tasks.sort(key=lambda x: (x["name"] or "", x.get("unit") or ""))
	return {"date": for_date, "tasks": tasks}
