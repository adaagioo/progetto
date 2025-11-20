# backend/app/repositories/production_plan_repo.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db


def _col():
	return get_db()["production_plans"]


def _as_id(doc: dict) -> dict:
	"""Convert MongoDB _id to id field"""
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def create_production_plan(
	restaurant_id: str,
	plan_date: date,
	items: List[Dict[str, Any]],
	status: str = "draft",
	notes: Optional[str] = None,
	based_on_forecast: Optional[Dict[str, Any]] = None
) -> str:
	"""Create a new production plan"""
	doc = {
		"restaurantId": restaurant_id,
		"date": plan_date.isoformat(),
		"items": items,
		"status": status,
		"notes": notes,
		"basedOnForecast": based_on_forecast,
		"createdAt": datetime.now(tz=timezone.utc),
		"updatedAt": None
	}
	result = await _col().insert_one(doc)
	return str(result.inserted_id)


async def get_production_plan(plan_id: str, restaurant_id: str) -> Optional[dict]:
	"""Get a specific production plan by ID"""
	doc = await _col().find_one({
		"_id": ObjectId(plan_id),
		"restaurantId": restaurant_id
	})
	return _as_id(doc)


async def get_production_plan_by_date(restaurant_id: str, plan_date: date) -> Optional[dict]:
	"""Get production plan for a specific date"""
	doc = await _col().find_one({
		"restaurantId": restaurant_id,
		"date": plan_date.isoformat()
	})
	return _as_id(doc)


async def list_production_plans(
	restaurant_id: str,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
	status: Optional[str] = None
) -> List[dict]:
	"""List production plans with optional filters"""
	query = {"restaurantId": restaurant_id}

	if start_date or end_date:
		date_filter = {}
		if start_date:
			date_filter["$gte"] = start_date.isoformat()
		if end_date:
			date_filter["$lte"] = end_date.isoformat()
		query["date"] = date_filter

	if status:
		query["status"] = status

	cursor = _col().find(query).sort("date", -1)
	return [_as_id(doc) async for doc in cursor]


async def update_production_plan(
	plan_id: str,
	restaurant_id: str,
	update_data: Dict[str, Any]
) -> bool:
	"""Update a production plan"""
	update_data["updatedAt"] = datetime.now(tz=timezone.utc)
	result = await _col().update_one(
		{"_id": ObjectId(plan_id), "restaurantId": restaurant_id},
		{"$set": update_data}
	)
	return result.matched_count > 0


async def delete_production_plan(plan_id: str, restaurant_id: str) -> bool:
	"""Delete a production plan"""
	result = await _col().delete_one({
		"_id": ObjectId(plan_id),
		"restaurantId": restaurant_id
	})
	return result.deleted_count > 0


async def upsert_production_plan(
	restaurant_id: str,
	plan_date: date,
	items: List[Dict[str, Any]],
	status: str = "draft",
	notes: Optional[str] = None,
	based_on_forecast: Optional[Dict[str, Any]] = None
) -> str:
	"""Create or update production plan for a specific date"""
	existing = await get_production_plan_by_date(restaurant_id, plan_date)

	if existing:
		# Update existing plan
		update_data = {
			"items": items,
			"status": status,
		}
		if notes is not None:
			update_data["notes"] = notes
		if based_on_forecast is not None:
			update_data["basedOnForecast"] = based_on_forecast

		await update_production_plan(existing["id"], restaurant_id, update_data)
		return existing["id"]
	else:
		# Create new plan
		return await create_production_plan(
			restaurant_id, plan_date, items, status, notes, based_on_forecast
		)
