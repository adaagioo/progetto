# backend/app/services/recipes_service.py
from __future__ import annotations
from typing import List, Optional
from backend.app.repositories.recipes_repo import find_many, find_one, insert_one, update_one, delete_one
from backend.app.db.mongo import get_db
from bson import ObjectId


async def _compute_recipe_costs(doc: dict) -> dict:
	"""
	Compute recipe cost fields from its items.

	Calculates:
	- totalCost: Sum of all ingredient/preparation costs
	- costPerPortion: totalCost / portions
	- priceWithoutVat: sellingPrice / (1 + vatPct/100)
	- foodCostPct: (costPerPortion / sellingPrice) * 100

	Args:
		doc: Recipe document with items list

	Returns:
		Recipe document with computed cost fields
	"""
	db = get_db()
	total_cost = 0.0

	# Sum up costs from all items
	for item in doc.get("items", []):
		item_type = item.get("type")
		item_id = item.get("itemId")
		qty_per_portion = item.get("qtyPerPortion", 0.0)

		try:
			if item_type == "ingredient":
				# Get ingredient cost
				ingredient = await db.ingredients.find_one({"_id": ObjectId(item_id)})
				if ingredient:
					# Use effectiveUnitCost (includes waste) if available
					unit_cost = ingredient.get("effectiveUnitCost") or ingredient.get("unitCost", 0.0)
					item_cost = unit_cost * qty_per_portion
					total_cost += item_cost

			elif item_type == "preparation":
				# Get preparation cost
				preparation = await db.preparations.find_one({"_id": ObjectId(item_id)})
				if preparation:
					prep_cost = preparation.get("cost", 0.0)
					# prep_cost is usually for the whole batch, so multiply by qty
					item_cost = prep_cost * qty_per_portion
					total_cost += item_cost

		except Exception:
			# If we can't find the item or calculate cost, skip it
			continue

	# Calculate derived fields
	portions = doc.get("portions", 1)
	cost_per_portion = total_cost / portions if portions > 0 else 0.0

	selling_price = doc.get("sellingPrice")
	vat_pct = doc.get("vatPct", 22.0)

	# Price without VAT
	price_without_vat = None
	if selling_price is not None and selling_price > 0:
		price_without_vat = selling_price / (1 + vat_pct / 100)

	# Food cost percentage
	food_cost_pct = None
	if selling_price is not None and selling_price > 0:
		food_cost_pct = (cost_per_portion / selling_price) * 100

	# Update document with calculated fields
	doc["totalCost"] = round(total_cost, 4)
	doc["costPerPortion"] = round(cost_per_portion, 4)
	if price_without_vat is not None:
		doc["priceWithoutVat"] = round(price_without_vat, 4)
	if food_cost_pct is not None:
		doc["foodCostPct"] = round(food_cost_pct, 2)

	return doc


async def _compute_recipe_costs_batch(recipes: List[dict]) -> List[dict]:
	"""
	Optimized batch version of _compute_recipe_costs to avoid N+1 queries.

	Collects all item IDs, fetches ingredients/preparations in 2 queries,
	then computes costs for all recipes using in-memory lookups.
	"""
	if not recipes:
		return []

	db = get_db()

	# Collect all unique ingredient and preparation IDs from all recipes
	ingredient_ids = set()
	preparation_ids = set()

	for recipe in recipes:
		for item in recipe.get("items", []):
			item_type = item.get("type")
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
		async for prep in cursor:
			preparations_map[str(prep["_id"])] = prep

	# Now compute costs for each recipe using in-memory lookups
	result = []
	for recipe in recipes:
		total_cost = 0.0

		for item in recipe.get("items", []):
			item_type = item.get("type")
			item_id = item.get("itemId")
			qty_per_portion = item.get("qtyPerPortion", 0.0)

			try:
				if item_type == "ingredient":
					ingredient = ingredients_map.get(item_id)
					if ingredient:
						unit_cost = ingredient.get("effectiveUnitCost") or ingredient.get("unitCost", 0.0)
						item_cost = unit_cost * qty_per_portion
						total_cost += item_cost

				elif item_type == "preparation":
					preparation = preparations_map.get(item_id)
					if preparation:
						prep_cost = preparation.get("cost", 0.0)
						item_cost = prep_cost * qty_per_portion
						total_cost += item_cost

			except Exception:
				continue

		# Calculate derived fields
		portions = recipe.get("portions", 1)
		cost_per_portion = total_cost / portions if portions > 0 else 0.0

		selling_price = recipe.get("sellingPrice")
		vat_pct = recipe.get("vatPct", 22.0)

		# Price without VAT
		price_without_vat = None
		if selling_price is not None and selling_price > 0:
			price_without_vat = selling_price / (1 + vat_pct / 100)

		# Food cost percentage
		food_cost_pct = None
		if selling_price is not None and selling_price > 0:
			food_cost_pct = (cost_per_portion / selling_price) * 100

		# Update document with calculated fields
		recipe["totalCost"] = round(total_cost, 4)
		recipe["costPerPortion"] = round(cost_per_portion, 4)
		if price_without_vat is not None:
			recipe["priceWithoutVat"] = round(price_without_vat, 4)
		if food_cost_pct is not None:
			recipe["foodCostPct"] = round(food_cost_pct, 2)

		result.append(recipe)

	return result


async def list_recipes(restaurant_id: str) -> List[dict]:
	recipes = await find_many(restaurant_id)
	return await _compute_recipe_costs_batch(recipes)


async def get_recipe(restaurant_id: str, recipe_id: str) -> Optional[dict]:
	recipe = await find_one(restaurant_id, recipe_id)
	return await _compute_recipe_costs(recipe) if recipe else None


async def create_recipe(doc: dict) -> str:
	# Compute costs before storing (optional - could compute on-the-fly)
	doc = await _compute_recipe_costs(doc)
	return await insert_one(doc)


async def update_recipe(restaurant_id: str, recipe_id: str, patch: dict) -> bool:
	# If items, portions, or price changed, recompute costs
	if any(k in patch for k in ["items", "portions", "sellingPrice", "vatPct"]):
		current = await find_one(restaurant_id, recipe_id)
		if current:
			merged = {**current, **patch}
			merged = await _compute_recipe_costs(merged)
			# Update patch with computed values
			patch["totalCost"] = merged.get("totalCost")
			patch["costPerPortion"] = merged.get("costPerPortion")
			if "priceWithoutVat" in merged:
				patch["priceWithoutVat"] = merged["priceWithoutVat"]
			if "foodCostPct" in merged:
				patch["foodCostPct"] = merged["foodCostPct"]

	return await update_one(restaurant_id, recipe_id, patch)


async def delete_recipe(restaurant_id: str, recipe_id: str) -> bool:
	return await delete_one(restaurant_id, recipe_id)
