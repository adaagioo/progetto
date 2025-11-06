# backend/app/api/V1/pl.py
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.pl import PLResponse
from backend.app.services.pl_service import compute_pl

router = APIRouter()
RESOURCE = "pl"


@router.get("/pl", response_model=PLResponse)
async def pl_get(start: date = Query(...), end: date = Query(...), user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	revenue, cogs, wastage_cost = await compute_pl(start, end)
	gross = revenue - cogs - wastage_cost
	return PLResponse(start=start, end=end, revenue=revenue, costOfGoods=cogs, wastageCost=wastage_cost,
	                  grossMargin=gross)
