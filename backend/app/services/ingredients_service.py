# backend/app/services/ingredients_service.py
from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from backend.app.repositories.ingredients_repo import find_many, find_one, insert_one, update_one, delete_one


def _compute_costs(doc: dict) -> dict:
	"""Compute unitCost and effectiveUnitCost from packSize, packCost, and wastePct"""
	pack_size = doc.get("packSize", 1.0)
	pack_cost = doc.get("packCost", 0.0)
	waste_pct = doc.get("wastePct", 0.0)

	# Avoid division by zero
	if pack_size > 0:
		unit_cost = pack_cost / pack_size
	else:
		unit_cost = 0.0

	# Apply waste percentage
	effective_unit_cost = unit_cost * (1 + waste_pct / 100)

	doc["unitCost"] = round(unit_cost, 4)
	doc["effectiveUnitCost"] = round(effective_unit_cost, 4)

	return doc


async def list_ingredients(restaurant_id: str) -> List[dict]:
	ingredients = await find_many(restaurant_id)
	return [_compute_costs(ing) for ing in ingredients]


async def get_ingredient(restaurant_id: str, ingredient_id: str) -> Optional[dict]:
	ing = await find_one(restaurant_id, ingredient_id)
	return _compute_costs(ing) if ing else None


async def create_ingredient(doc: dict) -> str:
	# Add computed fields and timestamp
	doc = _compute_costs(doc)
	doc["createdAt"] = datetime.now(timezone.utc).isoformat()
	return await insert_one(doc)


async def update_ingredient(restaurant_id: str, ingredient_id: str, patch: dict) -> bool:
	# If pack-related fields are updated, we need to recompute costs
	if any(k in patch for k in ["packSize", "packCost", "wastePct"]):
		# Fetch current ingredient
		current = await find_one(restaurant_id, ingredient_id)
		if current:
			# Merge patch with current values
			merged = {**current, **patch}
			merged = _compute_costs(merged)
			# Update patch with computed values
			patch["unitCost"] = merged["unitCost"]
			patch["effectiveUnitCost"] = merged["effectiveUnitCost"]

	return await update_one(restaurant_id, ingredient_id, patch)


async def delete_ingredient(restaurant_id: str, ingredient_id: str) -> bool:
	return await delete_one(restaurant_id, ingredient_id)
