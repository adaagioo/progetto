# backend/app/repositories/order_list_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from bson import ObjectId
from backend.app.db.mongo import get_db


async def compute_order_list(for_date: date, restaurant_id: str) -> Dict[str, Any]:
	"""
	Compute order list based on:
	1. Current inventory levels aggregated by ingredient
	2. Planned consumption from production plans (for_date and next few days)
	3. Reorder levels from ingredients collection

	Returns items that need to be ordered.
	"""
	db = get_db()

	# 1. Aggregate current inventory by ingredientId
	inventory_pipeline = [
		{"$match": {"restaurantId": restaurant_id}},
		{"$group": {
			"_id": "$ingredientId",
			"totalQty": {"$sum": "$qty"},
			"unit": {"$first": "$unit"}
		}}
	]

	inventory_cursor = db.inventory.aggregate(inventory_pipeline)
	inventory_by_ingredient: Dict[str, Dict[str, Any]] = {}
	async for doc in inventory_cursor:
		ingredient_id = str(doc["_id"])
		inventory_by_ingredient[ingredient_id] = {
			"currentQty": float(doc.get("totalQty", 0.0)),
			"unit": doc.get("unit")
		}

	# 2. Calculate planned consumption from production plans (today + next 7 days)
	consumption_by_ingredient: Dict[str, float] = {}

	end_date = for_date + timedelta(days=7)
	production_plans_cursor = db.production_plans.find({
		"restaurantId": restaurant_id,
		"date": {"$gte": for_date.isoformat(), "$lte": end_date.isoformat()}
	})

	async for plan in production_plans_cursor:
		for item in plan.get("items", []):
			recipe_id = item.get("recipeId")
			quantity = float(item.get("quantity", 0))

			# Get recipe ingredients
			try:
				recipe = await db.recipes.find_one({"_id": ObjectId(recipe_id)})
			except:
				recipe = await db.recipes.find_one({"id": recipe_id})

			if recipe:
				for ingredient in recipe.get("ingredients", []):
					ingredient_id = ingredient.get("ingredientId")
					if not ingredient_id:
						continue

					ing_qty = float(ingredient.get("quantity", 0))
					total_needed = ing_qty * quantity

					consumption_by_ingredient[ingredient_id] = (
						consumption_by_ingredient.get(ingredient_id, 0.0) + total_needed
					)

	# 3. Load ingredients with reorder/target levels
	ingredients_cursor = db.ingredients.find({"restaurantId": restaurant_id})

	order_items: List[Dict[str, Any]] = []

	async for ingredient in ingredients_cursor:
		ingredient_id = str(ingredient["_id"])
		name = ingredient.get("name", "Unknown")
		unit = ingredient.get("unit")
		reorder_level = ingredient.get("reorderLevel", 0)
		target_level = ingredient.get("targetLevel", 0)
		supplier_id = ingredient.get("defaultSupplierId")

		# Skip if no reorder level set
		if not reorder_level or reorder_level <= 0:
			continue

		# Get current inventory
		current = inventory_by_ingredient.get(ingredient_id, {}).get("currentQty", 0.0)

		# Get planned consumption
		planned_consumption = consumption_by_ingredient.get(ingredient_id, 0.0)

		# Calculate projected level after consumption
		projected = current - planned_consumption

		# If projected level is below reorder level, add to order list
		if projected < reorder_level:
			# Calculate order quantity to reach target level
			order_qty = max(0, target_level - projected) if target_level > 0 else (reorder_level - projected)

			order_items.append({
				"inventoryId": ingredient_id,  # Actually ingredientId, but schema expects inventoryId
				"name": name,
				"quantity": round(order_qty, 2),
				"unit": unit,
				"supplierId": supplier_id,
				"currentStock": round(current, 2),
				"plannedConsumption": round(planned_consumption, 2),
				"projectedStock": round(projected, 2),
				"reorderLevel": reorder_level,
				"targetLevel": target_level
			})

	# Sort by urgency (lowest projected stock first)
	order_items.sort(key=lambda x: x["projectedStock"])

	return {"date": for_date, "items": order_items}


async def compute_order_forecast(start: date, days: int, restaurant_id: str) -> List[Dict[str, Any]]:
	"""Compute order forecast for multiple days"""
	out = []
	for i in range(days):
		current_date = start + timedelta(days=i)
		result = await compute_order_list(current_date, restaurant_id)
		items_count = len(result.get("items", []))
		out.append({"date": current_date, "itemsCount": items_count})
	return out
