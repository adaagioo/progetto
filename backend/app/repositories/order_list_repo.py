# backend/app/repositories/order_list_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


async def compute_order_list(for_date: date, restaurant_id: str) -> Dict[str, Any]:
	"""
	Compute order list based on:
	1. Current inventory levels aggregated by ingredient
	2. Planned consumption from production plans (for_date and next few days)
	3. Reorder levels from ingredients collection

	Returns items that need to be ordered.

	Args:
		for_date: Date for which to compute the order list
		restaurant_id: Restaurant ID to filter data

	Returns:
		Dictionary with 'date' and 'items' (list of items to order)
	"""
	if not restaurant_id:
		logger.error("compute_order_list called without restaurant_id")
		return {"date": for_date, "items": []}

	try:
		db = get_db()
	except Exception as e:
		logger.error(f"Failed to get database connection: {e}")
		return {"date": for_date, "items": []}

	# 1. Aggregate current inventory by ingredientId
	inventory_by_ingredient: Dict[str, Dict[str, Any]] = {}
	try:
		inventory_pipeline = [
			{"$match": {"restaurantId": restaurant_id}},
			{"$group": {
				"_id": "$ingredientId",
				"totalQty": {"$sum": "$qty"},
				"unit": {"$first": "$unit"}
			}}
		]

		inventory_cursor = db.inventory.aggregate(inventory_pipeline)
		async for doc in inventory_cursor:
			ingredient_id = str(doc.get("_id"))
			if ingredient_id:
				inventory_by_ingredient[ingredient_id] = {
					"currentQty": float(doc.get("totalQty", 0.0)),
					"unit": doc.get("unit")
				}
	except Exception as e:
		logger.error(f"Error aggregating inventory for restaurant {restaurant_id}: {e}")
		# Continue with empty inventory - will show all items need ordering

	# 2. Calculate planned consumption from production plans (today + next 7 days)
	consumption_by_ingredient: Dict[str, float] = {}

	try:
		end_date = for_date + timedelta(days=7)
		production_plans_cursor = db.production_plans.find({
			"restaurantId": restaurant_id,
			"date": {"$gte": for_date.isoformat(), "$lte": end_date.isoformat()}
		})

		async for plan in production_plans_cursor:
			for item in plan.get("items", []):
				recipe_id = item.get("recipeId")
				if not recipe_id:
					continue

				quantity = float(item.get("quantity", 0))
				if quantity <= 0:
					continue

				# Get recipe ingredients
				recipe = None
				try:
					recipe = await db.recipes.find_one({"_id": ObjectId(recipe_id)})
				except Exception:
					try:
						recipe = await db.recipes.find_one({"id": recipe_id})
					except Exception as e:
						logger.warning(f"Failed to find recipe {recipe_id}: {e}")
						continue

				if not recipe:
					logger.warning(f"Recipe not found: {recipe_id}")
					continue

				for ingredient in recipe.get("ingredients", []):
					ingredient_id = ingredient.get("ingredientId")
					if not ingredient_id:
						continue

					try:
						ing_qty = float(ingredient.get("quantity", 0))
						total_needed = ing_qty * quantity

						consumption_by_ingredient[ingredient_id] = (
							consumption_by_ingredient.get(ingredient_id, 0.0) + total_needed
						)
					except (ValueError, TypeError) as e:
						logger.warning(f"Invalid quantity for ingredient {ingredient_id}: {e}")
						continue
	except Exception as e:
		logger.error(f"Error calculating consumption for restaurant {restaurant_id}: {e}")
		# Continue with empty consumption

	# 3. Load ingredients with reorder/target levels
	order_items: List[Dict[str, Any]] = []

	try:
		ingredients_cursor = db.ingredients.find({"restaurantId": restaurant_id})

		async for ingredient in ingredients_cursor:
			try:
				ingredient_id = str(ingredient.get("_id", ""))
				if not ingredient_id:
					continue

				name = ingredient.get("name", "Unknown")
				unit = ingredient.get("unit")

				# Safely parse reorder/target levels
				try:
					reorder_level = float(ingredient.get("reorderLevel", 0))
					target_level = float(ingredient.get("targetLevel", 0))
				except (ValueError, TypeError):
					logger.warning(f"Invalid reorder/target level for ingredient {ingredient_id}")
					continue

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
						"unit": unit or "unit",  # Provide default if missing
						"supplierId": supplier_id,
						"currentStock": round(current, 2),
						"plannedConsumption": round(planned_consumption, 2),
						"projectedStock": round(projected, 2),
						"reorderLevel": reorder_level,
						"targetLevel": target_level
					})
			except Exception as e:
				logger.warning(f"Error processing ingredient: {e}")
				continue

		# Sort by urgency (lowest projected stock first)
		order_items.sort(key=lambda x: x.get("projectedStock", 0))
	except Exception as e:
		logger.error(f"Error loading ingredients for restaurant {restaurant_id}: {e}")

	logger.info(f"Computed order list for {for_date}: {len(order_items)} items need ordering")
	return {"date": for_date, "items": order_items}


async def compute_order_forecast(start: date, days: int, restaurant_id: str) -> List[Dict[str, Any]]:
	"""
	Compute order forecast for multiple consecutive days.

	This function generates a forecast showing how many items will need to be ordered
	for each day in the specified range. Useful for planning ahead and understanding
	ordering patterns.

	Args:
		start: Starting date for the forecast
		days: Number of consecutive days to forecast (1-31)
		restaurant_id: Restaurant ID to filter data

	Returns:
		List of dictionaries, each containing:
			- date: The forecast date
			- itemsCount: Number of items that need ordering on that date

	Example:
		>>> forecast = await compute_order_forecast(date(2025, 1, 20), 7, "rest123")
		>>> forecast[0]
		{"date": date(2025, 1, 20), "itemsCount": 5}
	"""
	out = []
	for i in range(days):
		current_date = start + timedelta(days=i)
		result = await compute_order_list(current_date, restaurant_id)
		items_count = len(result.get("items", []))
		out.append({"date": current_date, "itemsCount": items_count})
	return out
