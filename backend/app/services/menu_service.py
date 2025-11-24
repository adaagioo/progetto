# backend/app/services/menu_service.py
from __future__ import annotations
from typing import Dict, Any
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.utils.units import normalize_quantity_to_base_unit


async def _find_by_id(collection, entity_id: str, additional_filters: dict = None):
	"""
	Try to find entity by both _id (ObjectId) and id (string) for compatibility.
	"""
	db = get_db()
	coll = db[collection]

	# Try _id as ObjectId first
	try:
		query = {"_id": ObjectId(entity_id)}
		if additional_filters:
			query.update(additional_filters)
		result = await coll.find_one(query, {"_id": 0})
		if result:
			return result
	except:
		pass

	# Fallback to string id field
	query = {"id": entity_id}
	if additional_filters:
		query.update(additional_filters)
	return await coll.find_one(query, {"_id": 0})


async def populate_menu_item_data(menu_item: dict) -> dict:
	"""
	Populate menu item with data from the referenced entity and compute availability.

	Args:
		menu_item: MenuItem dict with refType and refId

	Returns:
		Enhanced menu_item dict with populated fields
	"""
	db = get_db()
	ref_type = menu_item["refType"]
	ref_id = menu_item["refId"]

	# Initialize populated fields
	populated = {
		**menu_item,
		"name": None,
		"category": None,
		"recipeType": None,
		"computedCost": None,
		"allergens": [],
		"otherAllergens": [],
		"availabilityStatus": "unknown",
		"feasiblePortions": 0
	}

	try:
		if ref_type == "ingredient":
			ingredient = await _find_by_id("ingredients", ref_id)
			if ingredient:
				populated["name"] = ingredient["name"]
				populated["category"] = ingredient.get("category", "food")
				populated["computedCost"] = ingredient.get("effectiveUnitCost", ingredient.get("unitCost", 0))
				populated["allergens"] = ingredient.get("allergens", [])
				populated["otherAllergens"] = ingredient.get("otherAllergens", [])

				# Availability: check inventory
				inventory = await db.inventory.find_one({
					"ingredientId": ref_id,
					"restaurantId": ingredient["restaurantId"]
				})
				qty_on_hand = inventory.get("qty", 0) if inventory else 0
				if qty_on_hand <= 0:
					populated["availabilityStatus"] = "out"
					populated["feasiblePortions"] = 0
				elif qty_on_hand < 5:
					populated["availabilityStatus"] = "low"
					populated["feasiblePortions"] = int(qty_on_hand)
				else:
					populated["availabilityStatus"] = "available"
					populated["feasiblePortions"] = int(qty_on_hand)

		elif ref_type == "preparation":
			preparation = await _find_by_id("preparations", ref_id)
			if preparation:
				populated["name"] = preparation["name"]
				populated["category"] = "food"
				populated["computedCost"] = preparation.get("cost", 0)
				populated["allergens"] = preparation.get("allergens", [])
				populated["otherAllergens"] = preparation.get("otherAllergens", [])

				# Simplified availability check
				can_make = True
				min_portions = float('inf')

				for item in preparation.get("items", []):
					ingredient = await _find_by_id("ingredients", item["ingredientId"])
					if not ingredient:
						can_make = False
						break

					inventory = await db.inventory.find_one({
						"ingredientId": item["ingredientId"],
						"restaurantId": preparation["restaurantId"]
					})
					qty_on_hand = inventory.get("qty", 0) if inventory else 0

					# Normalize inventory quantity to match item unit
					normalized_qty = normalize_quantity_to_base_unit(
						qty_on_hand,
						ingredient.get("unit", "kg"),
						item.get("unit", "kg")
					)

					if normalized_qty <= 0:
						can_make = False
						break

					portions_possible = int(normalized_qty / item["qty"]) if item["qty"] > 0 else 0
					min_portions = min(min_portions, portions_possible)

				if not can_make or min_portions == 0:
					populated["availabilityStatus"] = "out"
					populated["feasiblePortions"] = 0
				elif min_portions < 5:
					populated["availabilityStatus"] = "low"
					populated["feasiblePortions"] = min_portions
				else:
					populated["availabilityStatus"] = "available"
					populated["feasiblePortions"] = min_portions

		elif ref_type == "recipe":
			recipe = await _find_by_id("recipes", ref_id)
			if recipe:
				populated["name"] = recipe["name"]
				populated["category"] = "food"
				populated["recipeType"] = recipe.get("recipeType", "kitchen")
				populated["computedCost"] = recipe.get("totalCost", 0)
				populated["allergens"] = recipe.get("allergens", [])
				populated["otherAllergens"] = recipe.get("otherAllergens", [])

				# Simplified availability for recipes
				populated["availabilityStatus"] = "available"
				populated["feasiblePortions"] = 100

	except Exception:
		# If any error, return with unknown status
		pass

	return populated
