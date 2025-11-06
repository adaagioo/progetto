# backend/app/api/V1/sales.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.sales import Sale, SaleCreate
from backend.app.repositories.sales_repo import create_sale, get_sale, list_sales, delete_sale
from backend.app.services.inventory_service import deduct_stock_for_recipe

router = APIRouter()
RESOURCE = "sales"


@router.post("/sales", response_model=Sale, status_code=201)
async def sales_create(payload: SaleCreate, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canCreate"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    sale_items = [i.model_dump() for i in payload.items]
    sid = await create_sale(payload.date, sale_items)
    for it in sale_items:
        rid = it.get("recipeId")
        qty = float(it.get("quantity", 0.0))
        if rid and qty > 0:
            await deduct_stock_for_recipe(rid, qty, actor_id=str(user.get("id")) if isinstance(user, dict) else None)
    doc = await get_sale(sid)
    return Sale(id=str(doc["_id"]), date=doc["date"], items=doc["items"], createdAt=doc["createdAt"])


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
    docs = await list_sales(start=start, end=end, limit=limit, skip=skip)
    return [Sale(id=str(d["_id"]), date=d["date"], items=d["items"], createdAt=d["createdAt"]) for d in docs]


@router.get("/sales/{sale_id}", response_model=Sale)
async def sales_get(sale_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canView"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    d = await get_sale(sale_id)
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    return Sale(id=str(d["_id"]), date=d["date"], items=d["items"], createdAt=d["createdAt"])


@router.delete("/sales/{sale_id}", status_code=204)
async def sales_delete(sale_id: str, user: dict = Depends(get_current_user)):
    access = await get_resource_access(user, RESOURCE)
    if not access.get("canDelete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    ok = await delete_sale(sale_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return None
