# backend/app/repositories/pl_repo.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from backend.app.db.mongo import get_db


def _pl_snapshots_col():
	return get_db()["pl_snapshots"]


def _pl_col():
	return get_db()["pl"]


async def create_pl_snapshot(
	restaurant_id: str,
	period: dict,
	currency: str,
	display_locale: str,
	sales_turnover: float,
	sales_food_beverage: float,
	sales_delivery: float,
	cogs_food_beverage: float,
	cogs_raw_waste: float,
	opex_non_food: float,
	opex_platforms: float,
	labour_employees: float,
	labour_staff_meal: float,
	marketing_online_ads: float,
	marketing_free_items: float,
	rent_base_effective: float,
	rent_garden: float,
	other_total: float,
	notes: Optional[str] = None
) -> str:
	"""Create a P&L snapshot"""
	# Calculate totals
	cogs_total = cogs_food_beverage + cogs_raw_waste
	opex_total = opex_non_food + opex_platforms
	labour_total = labour_employees + labour_staff_meal
	marketing_total = marketing_online_ads + marketing_free_items
	rent_total = rent_base_effective + rent_garden

	# Calculate EBITDA
	ebitda = (sales_turnover - cogs_total - opex_total -
	          labour_total - marketing_total - rent_total - other_total)

	snapshot_id = str(uuid.uuid4())
	doc = {
		"id": snapshot_id,
		"restaurantId": restaurant_id,
		"period": period,
		"currency": currency,
		"displayLocale": display_locale,
		"sales_turnover": round(sales_turnover, 2),
		"sales_food_beverage": round(sales_food_beverage, 2),
		"sales_delivery": round(sales_delivery, 2),
		"cogs_food_beverage": round(cogs_food_beverage, 2),
		"cogs_raw_waste": round(cogs_raw_waste, 2),
		"cogs_total": round(cogs_total, 2),
		"opex_non_food": round(opex_non_food, 2),
		"opex_platforms": round(opex_platforms, 2),
		"opex_total": round(opex_total, 2),
		"labour_employees": round(labour_employees, 2),
		"labour_staff_meal": round(labour_staff_meal, 2),
		"labour_total": round(labour_total, 2),
		"marketing_online_ads": round(marketing_online_ads, 2),
		"marketing_free_items": round(marketing_free_items, 2),
		"marketing_total": round(marketing_total, 2),
		"rent_base_effective": round(rent_base_effective, 2),
		"rent_garden": round(rent_garden, 2),
		"rent_total": round(rent_total, 2),
		"other_total": round(other_total, 2),
		"kpi_ebitda": round(ebitda, 2),
		"notes": notes,
		"createdAt": datetime.now(timezone.utc).isoformat(),
		"updatedAt": None
	}

	await _pl_snapshots_col().insert_one(doc)
	return snapshot_id


async def get_pl_snapshot(snapshot_id: str, restaurant_id: str) -> Optional[Dict[str, Any]]:
	"""Get a P&L snapshot by ID"""
	return await _pl_snapshots_col().find_one(
		{"id": snapshot_id, "restaurantId": restaurant_id},
		{"_id": 0}
	)


async def list_pl_snapshots(
	restaurant_id: str,
	start_date: Optional[str] = None,
	end_date: Optional[str] = None,
	limit: int = 1000
) -> List[Dict[str, Any]]:
	"""List P&L snapshots, optionally filtered by date range"""
	query = {"restaurantId": restaurant_id}

	if start_date or end_date:
		query["period.start"] = {}
		if start_date:
			query["period.start"]["$gte"] = start_date
		if end_date:
			query["period.start"]["$lte"] = end_date

	cursor = _pl_snapshots_col().find(query, {"_id": 0}).sort("period.start", -1).limit(limit)
	return await cursor.to_list(length=limit)


async def delete_pl_snapshot(snapshot_id: str, restaurant_id: str) -> bool:
	"""Delete a P&L snapshot"""
	result = await _pl_snapshots_col().delete_one(
		{"id": snapshot_id, "restaurantId": restaurant_id}
	)
	return result.deleted_count == 1


# ========== LEGACY P&L OPERATIONS ==========

async def create_pl(
	restaurant_id: str,
	month: str,
	revenue: float,
	cogs: float,
	gross_margin: float,
	notes: Optional[str] = None
) -> str:
	"""Create a legacy P&L record"""
	pl_id = str(uuid.uuid4())
	doc = {
		"id": pl_id,
		"restaurantId": restaurant_id,
		"month": month,
		"revenue": revenue,
		"cogs": cogs,
		"grossMargin": gross_margin,
		"notes": notes,
		"createdAt": datetime.now(timezone.utc).isoformat()
	}

	await _pl_col().insert_one(doc)
	return pl_id


async def get_pl(pl_id: str, restaurant_id: str) -> Optional[Dict[str, Any]]:
	"""Get a P&L record by ID"""
	return await _pl_col().find_one(
		{"id": pl_id, "restaurantId": restaurant_id},
		{"_id": 0}
	)


async def list_pl(restaurant_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
	"""List all P&L records for a restaurant"""
	cursor = _pl_col().find(
		{"restaurantId": restaurant_id},
		{"_id": 0}
	).sort("month", -1).limit(limit)
	return await cursor.to_list(length=limit)


async def delete_pl(pl_id: str, restaurant_id: str) -> bool:
	"""Delete a P&L record"""
	result = await _pl_col().delete_one(
		{"id": pl_id, "restaurantId": restaurant_id}
	)
	return result.deleted_count == 1
