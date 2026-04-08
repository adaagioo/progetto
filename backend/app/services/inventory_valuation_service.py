# backend/app/services/inventory_valuation_service.py
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from backend.app.schemas.inventory_valuation import (
	ValuationSummaryResponse,
	ValuationTotalResponse,
	ValuationByCategoryItem,
	ExpiringItem,
	AdjustmentItem,
	AdjustmentResult,
	DependenciesResponse,
)
from backend.app.repositories.inventory_repo import (
	aggregate_valuation_summary,
	aggregate_valuation_by_category,
	find_expiring_inventory_items,
	apply_inventory_adjustments,
	lookup_inventory_dependencies,
)


async def get_valuation_summary(as_of: Optional[date]) -> ValuationSummaryResponse:
	doc = await aggregate_valuation_summary(as_of or date.today())
	return ValuationSummaryResponse(**doc)


async def get_valuation_total(as_of: Optional[date]) -> ValuationTotalResponse:
	from backend.app.db.mongo import get_db
	doc = await aggregate_valuation_summary(as_of or date.today())
	total_val = doc.get("total", 0.0)
	# Count items with negative quantity for frontend warning
	db = get_db()
	negative_count = await db.inventory.count_documents({"quantity": {"$lt": 0}})
	return ValuationTotalResponse(
		total=total_val,
		totalValue=total_val,
		negativeCount=negative_count
	)


async def get_valuation_by_category(as_of: Optional[date]) -> List[ValuationByCategoryItem]:
	items = await aggregate_valuation_by_category(as_of or date.today())
	return [ValuationByCategoryItem(**it) for it in items]


async def get_expiring_items(days: int) -> List[ExpiringItem]:
	items = await find_expiring_inventory_items(days)
	return [ExpiringItem(**it) for it in items]


async def apply_adjustments(adjustments: List[AdjustmentItem], actor_id: str | None) -> AdjustmentResult:
	ok, processed, failed = await apply_inventory_adjustments(adjustments, actor_id)
	return AdjustmentResult(ok=ok, processed=processed, failed=failed)


async def find_inventory_dependencies(inventory_id: str) -> DependenciesResponse:
	deps = await lookup_inventory_dependencies(inventory_id)
	return DependenciesResponse(**deps)
