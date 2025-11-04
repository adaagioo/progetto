# backend/app/schemas/receiving.py
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel


class ReceivingItem(BaseModel):
	inventoryId: str
	quantity: float
	unitCost: float


class ReceivingCreate(BaseModel):
	supplierId: str
	date: date
	items: List[ReceivingItem]


class Receiving(BaseModel):
	id: str
	supplierId: str
	date: date
	items: List[ReceivingItem]
	createdAt: datetime


class ReceivingAttachFileRequest(BaseModel):
	fileId: str
