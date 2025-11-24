# backend/app/services/production_plan_service.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from backend.app.repositories import production_plan_repo as repo
from backend.app.db.mongo import get_db


async def get_or_create_plan_for_date(restaurant_id: str, plan_date: date) -> dict:
	"""Get existing production plan or create empty one"""
	plan = await repo.get_production_plan_by_date(restaurant_id, plan_date)
	if plan:
		return plan

	# Create empty plan
	plan_id = await repo.create_production_plan(
		restaurant_id=restaurant_id,
		plan_date=plan_date,
		items=[],
		status="draft"
	)
	return await repo.get_production_plan(plan_id, restaurant_id)


async def populate_plan_items_with_recipe_data(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	"""Enrich production plan items with recipe names and metadata"""
	if not items:
		return []

	db = get_db()
	recipes_col = db["recipes"]

	populated = []
	for item in items:
		recipe_id = item.get("recipeId")
		if not recipe_id:
			populated.append(item)
			continue

		# Fetch recipe data
		from bson import ObjectId
		try:
			recipe = await recipes_col.find_one({"_id": ObjectId(recipe_id)})
		except:
			recipe = await recipes_col.find_one({"id": recipe_id})

		# Add recipe metadata to item
		enriched = {**item}
		if recipe:
			enriched["recipeName"] = recipe.get("name", "Unknown")
			enriched["recipeCategory"] = recipe.get("category")
			enriched["recipeType"] = recipe.get("recipeType")
		else:
			enriched["recipeName"] = "Unknown Recipe"

		populated.append(enriched)

	return populated


async def generate_plan_from_sales_forecast(
	restaurant_id: str,
	plan_date: date,
	forecast_days: int = 7
) -> Dict[str, Any]:
	"""
	Generate production plan based on sales forecast.
	For now, this is a placeholder that returns empty items.
	TODO: Implement actual forecast logic based on sales history.
	"""
	# Placeholder implementation
	# In the future, this should:
	# 1. Analyze sales data for the past N days/weeks
	# 2. Predict expected sales for plan_date
	# 3. Consider day of week, seasonality, etc.
	# 4. Generate recommended quantities for each recipe

	return {
		"date": plan_date,
		"items": [],
		"forecastMetadata": {
			"method": "placeholder",
			"confidence": 0.0,
			"basedOnDays": forecast_days,
			"message": "Forecast not yet implemented"
		}
	}


async def validate_recipe_exists(recipe_id: str, restaurant_id: str) -> bool:
	"""Check if a recipe exists and belongs to the restaurant"""
	db = get_db()
	recipes_col = db["recipes"]

	from bson import ObjectId
	try:
		recipe = await recipes_col.find_one({
			"_id": ObjectId(recipe_id),
			"restaurantId": restaurant_id
		})
	except:
		recipe = await recipes_col.find_one({
			"id": recipe_id,
			"restaurantId": restaurant_id
		})

	return recipe is not None
