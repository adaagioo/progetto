# backend/app/api/V1/inventory.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import List
from backend.app.schemas.inventory import Inventory, InventoryCreate
from backend.app.services.inventory_service import (
	list_inventory, get_inventory, create_inventory, delete_inventory_by_receiving
)
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

RESOURCE = "inventory"


@router.get("/inventory")
async def list_all(
	user: dict = Depends(get_current_user),
	flat: bool = False
):
	"""
	Get inventory items.
	By default, returns grouped by category {food: [...], beverage: [...], other: [...]}.
	Use ?flat=true to get a flat list instead.
	"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	items = await list_inventory(user["restaurantId"])

	# Convert all items to list of dicts
	from fastapi.encoders import jsonable_encoder

	all_items = []
	for item in items:
		item_dict = item.model_dump() if hasattr(item, 'model_dump') else item
		all_items.append(item_dict)

	logger.debug(f"Returning {len(all_items)} items as flat array")

	# Simply return the flat array - this is what the frontend expects for iteration
	return JSONResponse(content=jsonable_encoder(all_items))


@router.get("/inventory/expiring")
async def get_expiring_inventory(days: int = 3, user: dict = Depends(get_current_user)):
	"""Get count of items expiring within specified days (bucketed by day)"""
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	from backend.app.services.inventory_service import get_expiring_inventory_buckets

	try:
		result = await get_expiring_inventory_buckets(user["restaurantId"], days)
		return result
	except ValueError as e:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/inventory/{inv_id}", response_model=Inventory)
async def get_one(inv_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	doc = await get_inventory(user["restaurantId"], inv_id)
	if not doc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
	return doc


@router.post("/inventory", response_model=Inventory, status_code=status.HTTP_201_CREATED)
async def create(body: InventoryCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canCreate", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]

	# Add createdAt timestamp
	from datetime import datetime, timezone
	doc["createdAt"] = datetime.now(tz=timezone.utc)

	logger.debug(f"Creating inventory with: {doc}")

	new_id = await create_inventory(doc)
	created = await get_inventory(user["restaurantId"], new_id)

	# Ensure createdAt is serialized as string
	if created and "createdAt" in created:
		if hasattr(created["createdAt"], "isoformat"):
			created["createdAt"] = created["createdAt"].isoformat()

	return created


@router.delete("/inventory/by-receiving/{receiving_id}", status_code=status.HTTP_200_OK)
async def delete_by_receiving(receiving_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canDelete", False):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	deleted = await delete_inventory_by_receiving(user["restaurantId"], receiving_id)
	return {"deleted": deleted}
