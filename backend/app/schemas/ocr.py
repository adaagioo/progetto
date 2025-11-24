# backend/app/schemas/ocr.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


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


class OCRMappingRecord(BaseModel):
	key: str
	inventoryId: str
	defaultUnit: Optional[str] = None
	supplierId: Optional[str] = None


class OCRItemMatch(BaseModel):
	inventoryId: str
	name: str
	score: float = Field(ge=0.0, le=1.0)


class OCRParsedItem(BaseModel):
	name: str
	qty: float
	unit: str
	unitCost: float
	matches: List[OCRItemMatch] = []


class OCRParsedDocument(BaseModel):
	date: Optional[str] = None
	supplier: Optional[str] = None
	currency: Optional[str] = None
	items: List[OCRParsedItem] = []


class OCRCreateReceivingRequest(BaseModel):
	fileId: str
	language: Optional[str] = None
	items: List[OCRParsedItem]


def rebuild_models() -> None:
	OCRLine.model_rebuild()
	OCRResult.model_rebuild()
	OCRItemMatch.model_rebuild()
	OCRParsedItem.model_rebuild()
	OCRParsedDocument.model_rebuild()
	OCRCreateReceivingRequest.model_rebuild()
