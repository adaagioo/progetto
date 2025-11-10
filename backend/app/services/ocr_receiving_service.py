# backend/app/services/ocr_receiving_service.py
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
from backend.app.schemas.receiving import ReceivingCreate, ReceivingItem
from backend.app.schemas.ocr import OCRCreateReceivingRequest
from backend.app.repositories.receiving_repo import create_receiving


async def create_receiving_from_ocr(payload: OCRCreateReceivingRequest) -> str:
	items: List[Dict[str, Any]] = []
	for line in payload.items:
		items.append({
			"inventoryId": line.inventoryId,
			"quantity": line.quantity,
			"unit": line.unit,
			"unitCost": line.unitCost,
			"supplierId": line.supplierId,
			"notes": line.notes,
		})

	rec_id = await create_receiving(payload.date, items, datetime.utcnow())
	return rec_id
