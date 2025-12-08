# backend/app/services/pl_service.py
from __future__ import annotations
from datetime import date, datetime
from typing import Tuple
from backend.app.db.mongo import get_db


async def compute_pl(restaurant_id: str, start: date, end: date) -> Tuple[float, float, float]:
	db = get_db()
	revenue = 0.0
	async for s in db["sales"].aggregate([
		{"$match": {"restaurantId": restaurant_id, "date": {"$gte": start, "$lte": end}}},
		{"$unwind": "$items"},
		{"$group": {"_id": None, "sum": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}}}},
	]):
		revenue = float(s.get("sum", 0.0))
	cogs = 0.0
	wastage_cost = 0.0
	return revenue, cogs, wastage_cost
