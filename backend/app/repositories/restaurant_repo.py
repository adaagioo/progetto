# backend/app/repositories/restaurant_repo.py
from __future__ import annotations
from typing import Optional
from backend.app.db.mongo import get_db


def _restaurants():
	return get_db()["restaurants"]


async def find_by_id(restaurant_id: str) -> Optional[dict]:
	"""Find restaurant by ID"""
	return await _restaurants().find_one({"id": restaurant_id}, {"_id": 0})


async def upsert(restaurant_id: str, data: dict) -> dict:
	"""Update or insert restaurant data. Returns the updated/created restaurant."""
	update_data = {**data}
	update_data["id"] = restaurant_id

	# Set default subscription status if creating new
	if "subscriptionStatus" not in update_data:
		update_data["subscriptionStatus"] = "active"

	await _restaurants().update_one(
		{"id": restaurant_id},
		{"$set": update_data},
		upsert=True
	)

	# Return updated document
	return await find_by_id(restaurant_id)
