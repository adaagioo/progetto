# backend/app/schemas/ocr.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class OCRStartRequest(BaseModel):
	fileId: str
	language: str = "eng"


class OCRLine(BaseModel):
	text: str
	confidence: float


class OCRResult(BaseModel):
	ok: bool
	lines: List[OCRLine] = []
	meta: Dict[str, Any] = {}


class OCRMappingSuggestion(BaseModel):
	key: str
	value: str


class OCRMappingRule(BaseModel):
	key: str
	inventoryId: str
	defaultUnit: Optional[str] = None


class OCRSaveMappingsRequest(BaseModel):
	supplierId: Optional[str] = None
	rules: List[OCRMappingRule]


class OCRReceivingLine(BaseModel):
	inventoryId: str
	quantity: float
	unit: Optional[str] = None
	unitCost: Optional[float] = None
	notes: Optional[str] = None
	supplierId: Optional[str] = None


class OCRCreateReceivingRequest(BaseModel):
	date: date
	items: List[OCRReceivingLine]


class OCRMappingRecord(BaseModel):
	key: str
	inventoryId: str
	defaultUnit: Optional[str] = None
	supplierId: Optional[str] = None
