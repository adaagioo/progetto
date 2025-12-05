# backend/app/services/preparations_service.py
from __future__ import annotations
from typing import List, Optional
from backend.app.repositories.preparations_repo import find_many, find_one, insert_one, update_one, delete_one
from backend.app.db.mongo import get_db
from bson import ObjectId


async def _compute_preparation_costs(doc: dict) -> dict:
	"""
	Compute preparation cost fields from its items.

	Calculates:
	- cost: Sum of all ingredient/nested preparation costs
	- costPerPortion: cost / portions

	Args:
		doc: Preparation document with items list

	Returns:
		Preparation document with computed cost fields
	"""
	db = get_db()
	total_cost = 0.0

	# Sum up costs from all items
	for item in doc.get("items", []):
		item_type = item.get("type", "ingredient")
		item_id = item.get("itemId")
		qty = item.get("qty", 0.0)

		try:
			if item_type == "ingredient":
				# Get ingredient cost
				ingredient = await db.ingredients.find_one({"_id": ObjectId(item_id)})
				if ingredient:
					# Use effectiveUnitCost (includes waste) if available, fallback to unitCost
					unit_cost = ingredient.get("effectiveUnitCost") or ingredient.get("unitCost", 0.0)
					item_cost = unit_cost * qty
					total_cost += item_cost

			elif item_type == "preparation":
				# Get nested preparation cost (preparations can contain other preparations)
				preparation = await db.preparations.find_one({"_id": ObjectId(item_id)})
				if preparation:
					# Use costPerPortion if available, fallback to cost
					prep_cost = preparation.get("costPerPortion") or preparation.get("cost", 0.0)
					item_cost = prep_cost * qty
					total_cost += item_cost

		except Exception:
			# If we can't find the item or calculate cost, skip it
			continue

	# Calculate cost per portion
	portions = doc.get("portions", 1)
	cost_per_portion = total_cost / portions if portions > 0 else 0.0

	# Update document with calculated fields
	doc["cost"] = round(total_cost, 4)
	doc["costPerPortion"] = round(cost_per_portion, 4)

	return doc


async def _compute_preparation_costs_batch(preparations: List[dict]) -> List[dict]:
	"""
	Optimized batch version of _compute_preparation_costs to avoid N+1 queries.

	Collects all item IDs, fetches ingredients/preparations in 2 queries,
	then computes costs for all preparations using in-memory lookups.
	"""
	if not preparations:
		return []

	db = get_db()

	# Collect all unique ingredient and preparation IDs from all preparations
	ingredient_ids = set()
	preparation_ids = set()

	for prep in preparations:
		for item in prep.get("items", []):
			item_type = item.get("type", "ingredient")
			item_id = item.get("itemId")
			try:
				if item_type == "ingredient":
					ingredient_ids.add(ObjectId(item_id))
				elif item_type == "preparation":
					preparation_ids.add(ObjectId(item_id))
			except Exception:
				continue

	# Fetch all ingredients and preparations in 2 queries (instead of N*M queries)
	ingredients_map = {}
	if ingredient_ids:
		cursor = db.ingredients.find({"_id": {"$in": list(ingredient_ids)}})
		async for ing in cursor:
			ingredients_map[str(ing["_id"])] = ing

	preparations_map = {}
	if preparation_ids:
		cursor = db.preparations.find({"_id": {"$in": list(preparation_ids)}})
		async for nested_prep in cursor:
			preparations_map[str(nested_prep["_id"])] = nested_prep

	# Now compute costs for each preparation using in-memory lookups
	result = []
	for prep in preparations:
		total_cost = 0.0

		for item in prep.get("items", []):
			item_type = item.get("type", "ingredient")
			item_id = item.get("itemId")
			qty = item.get("qty", 0.0)

			try:
				if item_type == "ingredient":
					ingredient = ingredients_map.get(item_id)
					if ingredient:
						unit_cost = ingredient.get("effectiveUnitCost") or ingredient.get("unitCost", 0.0)
						item_cost = unit_cost * qty
						total_cost += item_cost

				elif item_type == "preparation":
					preparation = preparations_map.get(item_id)
					if preparation:
						prep_cost = preparation.get("costPerPortion") or preparation.get("cost", 0.0)
						item_cost = prep_cost * qty
						total_cost += item_cost

			except Exception:
				continue

		# Calculate cost per portion
		portions = prep.get("portions", 1)
		cost_per_portion = total_cost / portions if portions > 0 else 0.0

		# Update document with calculated fields
		prep["cost"] = round(total_cost, 4)
		prep["costPerPortion"] = round(cost_per_portion, 4)

		result.append(prep)

	return result


async def list_preparations(restaurant_id: str) -> List[dict]:
	preparations = await find_many(restaurant_id)
	return await _compute_preparation_costs_batch(preparations)


async def get_preparation(restaurant_id: str, prep_id: str) -> Optional[dict]:
	preparation = await find_one(restaurant_id, prep_id)
	return await _compute_preparation_costs(preparation) if preparation else None


async def create_preparation(doc: dict) -> str:
	# Compute costs before storing
	doc = await _compute_preparation_costs(doc)
	return await insert_one(doc)


async def update_preparation(restaurant_id: str, prep_id: str, patch: dict) -> bool:
	# If items or portions changed, recompute costs
	if any(k in patch for k in ["items", "portions"]):
		current = await find_one(restaurant_id, prep_id)
		if current:
			merged = {**current, **patch}
			merged = await _compute_preparation_costs(merged)
			# Update patch with computed values
			patch["cost"] = merged.get("cost")
			patch["costPerPortion"] = merged.get("costPerPortion")

	return await update_one(restaurant_id, prep_id, patch)


async def delete_preparation(restaurant_id: str, prep_id: str) -> bool:
	return await delete_one(restaurant_id, prep_id)
