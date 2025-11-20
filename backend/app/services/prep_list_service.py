# backend/app/services/prep_list_service.py
from __future__ import annotations
from datetime import date
from typing import Dict, Any, List, Tuple
from bson import ObjectId
from backend.app.db.mongo import get_db


def _production_plans(): return get_db()["production_plans"]


def _recipes(): return get_db()["recipes"]


def _preps(): return get_db()["preparations"]


async def _load_production_plan(for_date: date) -> Dict[str, Any] | None:
	"""Load production plan for a specific date"""
	date_str = for_date.isoformat()
	return await _production_plans().find_one({"date": date_str})


async def _map_preparation_names(ids: List[ObjectId]) -> Dict[str, str]:
	names: Dict[str, str] = {}
	if not ids:
		return names
	async for p in _preps().find({"_id": {"$in": ids}}, projection={"name": 1}):
		names[str(p["_id"])] = p.get("name") or str(p["_id"])
	return names


async def compute_prep_list(for_date: date) -> Dict[str, Any]:
	"""Aggregate preparation tasks from the day's production plan.
	Assumptions:
	  - ProductionPlan: { date, items: [{ recipeId, quantity }] }
	  - Recipe: has ingredients[] where each ingredient may have preparationId, quantity, unit, name
	We aggregate tasks by preparationId (fallback by ingredient name).
	"""
	plan = await _load_production_plan(for_date)
	if not plan or not plan.get("items"):
		print(f"[PREP_LIST DEBUG] No production plan found for date {for_date}")
		return {"date": for_date, "tasks": []}

	print(f"[PREP_LIST DEBUG] Found production plan with {len(plan['items'])} items")

	# Collect all recipe ids
	recipe_ids = [ObjectId(i["recipeId"]) for i in plan["items"] if i.get("recipeId")]
	qty_by_recipe = {str(ObjectId(i["recipeId"])): float(i.get("quantity", 1.0)) for i in plan["items"] if
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
		resolved_name = t["name"]
		prep_id = t.get("preparationId")
		if prep_id:
			prep_id_str = str(prep_id) if isinstance(prep_id, ObjectId) else prep_id
			resolved_name = name_map.get(prep_id_str, t["name"])
		else:
			prep_id_str = None

		tasks.append({
			"preparationId": prep_id_str,  # Convert ObjectId to string
			"recipeId": str(t.get("recipeId")) if t.get("recipeId") else None,
			"name": resolved_name,
			"preparationName": resolved_name,  # Frontend expects this field
			"quantity": round(float(t["quantity"]), 4),
			"unit": t.get("unit"),
		})
	# Sort by name for stable output
	tasks.sort(key=lambda x: (x["name"] or "", x.get("unit") or ""))
	print(f"[PREP_LIST DEBUG] Computed {len(tasks)} tasks for date {for_date}")
	print(f"[PREP_LIST DEBUG] First task: {tasks[0] if tasks else 'none'}")
	return {"date": for_date, "tasks": tasks}
