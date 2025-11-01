# backend/app/api/V1/inventory.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.schemas.inventory import Inventory, InventoryCreate
from app.services.inventory_service import (
    list_inventory, get_inventory, create_inventory, delete_inventory_by_receiving
)
from app.deps.auth import get_current_user
from app.core.rbac_utils import get_resource_access

router = APIRouter()

RESOURCE = "inventory"

@router.get("/inventory", response_model=List[Inventory])
async def list_all(user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access["canView"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await list_inventory(user["restaurantId"])

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
    new_id = await create_inventory(doc)
    created = await get_inventory(user["restaurantId"], new_id)
    return created

@router.delete("/inventory/by-receiving/{receiving_id}", status_code=status.HTTP_200_OK)
async def delete_by_receiving(receiving_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access["canDelete"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    deleted = await delete_inventory_by_receiving(user["restaurantId"], receiving_id)
    return {"deleted": deleted}
