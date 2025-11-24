# backend/app/api/V1/inventory_admin.py
from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.inventory_admin import InventoryBulkUpdateRequest
from backend.app.repositories.inventory_repo import bulk_update_inventory

router = APIRouter()
RESOURCE = "inventory"


@router.post("/inventory/bulk-update", status_code=200)
async def inventory_bulk_update(payload: InventoryBulkUpdateRequest, user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canUpdate"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	ok, processed, failed = await bulk_update_inventory([i.model_dump(exclude_unset=True) for i in payload.items])
	return {"ok": ok, "processed": processed, "failed": failed}
