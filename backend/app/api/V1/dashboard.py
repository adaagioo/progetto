# backend/app/api/V1/dashboard.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.deps.auth import get_current_user
from backend.app.core.rbac_policies import get_resource_access
from backend.app.schemas.dashboard import KPIResponse
from backend.app.services.dashboard_service import get_kpis

router = APIRouter()
RESOURCE = "dashboard"


@router.get("/dashboard/kpis", response_model=KPIResponse)
async def dashboard_kpis(user: dict = Depends(get_current_user)):
	access = await get_resource_access(user, RESOURCE)
	if not access.get("canView"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
	data = await get_kpis()
	return KPIResponse(**data)
