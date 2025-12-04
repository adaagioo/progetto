# backend/app/api/V1/inventory_valuation.py
from __future__ import annotations
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.inventory_valuation import (
	ValuationSummaryResponse,
	ValuationTotalResponse,
	ValuationByCategoryItem,
	ValuationByCategoryResponse,
	ExpiringItem,
	AdjustmentItem,
	AdjustmentRequest,
	AdjustmentResult,
	DependenciesResponse,
)
from backend.app.services.inventory_valuation_service import (
	get_valuation_summary,
	get_valuation_total,
	get_valuation_by_category,
	get_expiring_items,
	apply_adjustments,
	find_inventory_dependencies,
)
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
RESOURCE = "inventory"


@router.get("/inventory/valuation/summary", response_model=ValuationSummaryResponse)
async def valuation_summary(
		asOf: Optional[date] = Query(None, description="Valuation date; defaults to today"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	result = await get_valuation_summary(asOf)
	logger.debug(f"Returning valuation summary: {result}")
	logger.debug(f"Summary model_dump: {result.model_dump()}")
	return result


@router.get("/inventory/valuation/total", response_model=ValuationTotalResponse)
async def valuation_total(
		asOf: Optional[date] = Query(None, description="Valuation date; defaults to today"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await get_valuation_total(asOf)


@router.get("/inventory/valuation/by-category", response_model=ValuationByCategoryResponse)
async def valuation_by_category(
		asOf: Optional[date] = Query(None, description="Valuation date; defaults to today"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	items = await get_valuation_by_category(asOf)
	return ValuationByCategoryResponse(items=items)


@router.get("/inventory/valuation/{category}")
async def valuation_by_specific_category(
		category: str,
		asOf: Optional[date] = Query(None, description="Valuation date; defaults to today"),
		user: dict = Depends(get_current_user),
):
	"""Get inventory valuation for a specific category (food, beverage, supplies)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	# Validate category
	valid_categories = ["food", "beverage", "supplies"]
	# Map legacy "nonfood" to "supplies" for backward compatibility
	if category == "nonfood":
		category = "supplies"
		logger.warning(f"Category 'nonfood' is deprecated, using 'supplies' instead")

	if category not in valid_categories:
		raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")

	# Get all items by category
	items = await get_valuation_by_category(asOf)

	# Filter by requested category (items are ValuationByCategoryItem objects)
	category_items = [item for item in items if item.category == category]

	# Calculate total for this category
	total_value = sum(item.total for item in category_items)

	return {
		"category": category,
		"totalValue": total_value,
		"itemCount": len(category_items),
		"items": [item.model_dump() for item in category_items]
	}


@router.get("/inventory/valuation", response_model=ValuationTotalResponse)
async def valuation_default(
		asOf: Optional[date] = Query(None, description="Valuation date; defaults to today"),
		user: dict = Depends(get_current_user),
):
	"""Get total inventory valuation (same as /inventory/valuation/total)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await get_valuation_total(asOf)


@router.get("/inventory/expiring", response_model=List[ExpiringItem])
async def inventory_expiring(
		days: int = Query(7, ge=1, le=90, description="Window in days to consider as expiring"),
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await get_expiring_items(days)


@router.get("/inventory/adjustments")
async def inventory_adjustments_list(user: dict = Depends(get_current_user)):
	"""Get list of inventory adjustments (placeholder - not yet implemented)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	# TODO: Implement adjustments history
	return {"adjustments": [], "message": "Adjustments history not yet implemented"}


@router.post("/inventory/adjustments", response_model=AdjustmentResult)
async def inventory_adjustments(
		payload: AdjustmentRequest,
		user: dict = Depends(get_current_user),
):
	"""Apply inventory adjustments"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await apply_adjustments(payload.items, actor_id=str(user.get("_id")))


@router.get("/inventory/{inventory_id}/dependencies", response_model=DependenciesResponse)
async def inventory_dependencies(
		inventory_id: str,
		user: dict = Depends(get_current_user),
):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	return await find_inventory_dependencies(inventory_id)
