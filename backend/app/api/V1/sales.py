# backend/app/api/V1/sales.py
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.sales import Sale, SaleCreate
from backend.app.repositories import sales_repo as repo
from backend.app.services.inventory_service import deduct_stock_for_recipe

router = APIRouter()
RESOURCE = "sales"


@router.post("/sales", response_model=Sale, status_code=201)
async def sales_create(payload: SaleCreate, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canCreate"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    sale_items = [i.model_dump() for i in payload.items]
    sale_doc = {
        "date": payload.date,
        "items": sale_items,
        "restaurantId": user["restaurantId"],
        "createdAt": datetime.now(tz=timezone.utc)
    }
    sid = await repo.insert_one(sale_doc)

    # Deduct stock with rollback on failure
    try:
        for it in sale_items:
            rid = it.get("recipeId")
            qty = float(it.get("quantity", 0.0))
            if rid and qty > 0:
                await deduct_stock_for_recipe(rid, qty, actor_id=str(user["_id"]))
    except Exception as e:
        # Rollback: delete the sale if stock deduction fails
        await repo.delete_one(user["restaurantId"], sid)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to deduct stock: {str(e)}"
        )

    doc = await repo.find_one(user["restaurantId"], sid)
    return Sale(**doc)


@router.get("/sales", response_model=List[Sale])
async def sales_list(
        start: Optional[date] = Query(None),
        end: Optional[date] = Query(None),
        limit: int = 100, skip: int = 0,
        user: dict = Depends(get_current_user),
):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canView"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    docs = await repo.find_many(user["restaurantId"], start=start, end=end, limit=limit, skip=skip)
    return [Sale(**d) for d in docs]


@router.get("/sales/{sale_id}", response_model=Sale)
async def sales_get(sale_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canView"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    d = await repo.find_one(user["restaurantId"], sale_id)
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    return Sale(**d)


@router.delete("/sales/{sale_id}", status_code=204)
async def sales_delete(sale_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canDelete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    ok = await repo.delete_one(user["restaurantId"], sale_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return None
