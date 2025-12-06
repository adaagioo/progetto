# backend/app/api/V1/restaurant.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.repositories import restaurant_repo as repo

router = APIRouter()


@router.get("/restaurant")
async def get_restaurant(user: dict = Depends(get_current_user)):
	"""Get restaurant details for the current user"""
	restaurant = await repo.find_by_id(user["restaurantId"])

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
	# Only allow certain fields to be updated
	allowed_fields = {"name", "currency", "locale", "address", "phone", "email"}
	update_data = {k: v for k, v in payload.items() if k in allowed_fields}

	if not update_data:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

	# Upsert (update or create) restaurant
	restaurant = await repo.upsert(user["restaurantId"], update_data)

	return restaurant
