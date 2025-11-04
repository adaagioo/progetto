# backend/app/repositories/order_list_repo.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import date, timedelta


# Placeholder repository - compute-on-read approach.
# Future: persist generated order lists into a collection if needed.

async def compute_order_list(for_date: date) -> Dict[str, Any]:
	# TODO: wire to inventory thresholds and menu requirements
	return {"date": for_date, "items": []}


async def compute_order_forecast(start: date, days: int) -> List[Dict[str, Any]]:
	out = []
	for i in range(days):
		out.append({"date": start + timedelta(days=i), "itemsCount": 0})
	return out
