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
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")

	items = await list_inventory(user["restaurantId"])

	# Convert all items to list of dicts
	from fastapi.encoders import jsonable_encoder

	all_items = []
	for item in items:
		item_dict = item.model_dump() if hasattr(item, 'model_dump') else item
		all_items.append(item_dict)

	print(f"[INVENTORY DEBUG] Returning {len(all_items)} items as flat array")

	# Simply return the flat array - this is what the frontend expects for iteration
	return JSONResponse(content=jsonable_encoder(all_items))


@router.get("/inventory/expiring")
async def get_expiring_inventory(days: int = 3, user: dict = Depends(get_current_user)):
	"""Get count of items expiring within specified days (bucketed by day)"""
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")

	from datetime import date, timedelta
	from backend.app.db.mongo import get_db

	db = get_db()
	inventory_items = await db.inventory.find({
		"restaurantId": user["restaurantId"],
		"expiryDate": {"$exists": True, "$ne": None}
	}).to_list(10000)

	today = date.today()
	buckets = {f"day{i}": 0 for i in range(1, days + 1)}

	for item in inventory_items:
		expiry_str = item.get("expiryDate")
		if not expiry_str:
			continue

		try:
			if isinstance(expiry_str, str):
				expiry_date = date.fromisoformat(expiry_str.split('T')[0])
			else:
				continue

			days_until_expiry = (expiry_date - today).days

			# Bucket items by days (1, 2, 3, etc.)
			if 0 <= days_until_expiry < days:
				bucket_key = f"day{days_until_expiry + 1}"
				if bucket_key in buckets:
					buckets[bucket_key] += 1

		except (ValueError, AttributeError):
			continue

	return {"buckets": buckets, "total": sum(buckets.values())}


@router.get("/inventory/{inv_id}", response_model=Inventory)
async def get_one(inv_id: str, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canView"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	doc = await get_inventory(user["restaurantId"], inv_id)
	if not doc:
		raise HTTPException(status_code=404, detail="Inventory record not found")
	return doc


@router.post("/inventory", response_model=Inventory, status_code=status.HTTP_201_CREATED)
async def create(body: InventoryCreate, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access["canCreate"]:
		raise HTTPException(status_code=403, detail="Forbidden")

	doc = body.model_dump()
	doc["restaurantId"] = user["restaurantId"]

	# Add createdAt timestamp
	from datetime import datetime
	doc["createdAt"] = datetime.utcnow()

	print(f"[INVENTORY DEBUG] Creating inventory with: {doc}")

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
	if not access["canDelete"]:
		raise HTTPException(status_code=403, detail="Forbidden")
	deleted = await delete_inventory_by_receiving(user["restaurantId"], receiving_id)
	return {"deleted": deleted}
