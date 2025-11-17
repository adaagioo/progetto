# backend/app/api/V1/restaurant.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.db.mongo import get_db

router = APIRouter()


@router.get("/restaurant")
async def get_restaurant(user: dict = Depends(get_current_user)):
	"""Get restaurant details for the current user"""
	db = get_db()
	restaurant = await db.restaurants.find_one(
		{"id": user["restaurantId"]},
		{"_id": 0}
	)

	if not restaurant:
		# Return a default restaurant if not found
		return {
			"id": user["restaurantId"],
			"name": "My Restaurant",
			"currency": "EUR",
			"locale": "it-IT",
			"subscriptionStatus": "active"
		}

	return restaurant


@router.put("/restaurant")
async def update_restaurant(payload: dict, user: dict = Depends(get_current_user)):
	"""Update restaurant details"""
	db = get_db()

	# Only allow certain fields to be updated
	allowed_fields = {"name", "currency", "locale", "address", "phone", "email"}
	update_data = {k: v for k, v in payload.items() if k in allowed_fields}

	if not update_data:
		raise HTTPException(status_code=400, detail="No valid fields to update")

	result = await db.restaurants.update_one(
		{"id": user["restaurantId"]},
		{"$set": update_data}
	)

	if result.matched_count == 0:
		# Create restaurant if it doesn't exist
		update_data["id"] = user["restaurantId"]
		update_data["subscriptionStatus"] = "active"
		await db.restaurants.insert_one(update_data)

	# Fetch and return updated restaurant
	restaurant = await db.restaurants.find_one(
		{"id": user["restaurantId"]},
		{"_id": 0}
	)

	return restaurant
