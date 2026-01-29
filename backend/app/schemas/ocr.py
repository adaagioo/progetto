# backend/app/schemas/ocr.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import date as date_type
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


class OCRLineItemFrontend(BaseModel):
	"""Line item format expected by frontend for create-receiving"""
	ingredientId: str
	description: Optional[str] = None
	qty: float
	unit: str = "kg"
	unitPrice: float = 0
	packFormat: Optional[str] = None


class OCRCreateReceivingFrontend(BaseModel):
	"""Create receiving request format from frontend (DocumentImport.js)"""
	supplierId: str
	date: Optional[str] = None
	invoiceNumber: Optional[str] = None
	documentType: Optional[str] = None
	category: str = "food"
	lineItems: List[OCRLineItemFrontend]


class OCRProcessResponseOcr(BaseModel):
	"""OCR portion of the process response"""
	lines: List[OCRLine] = []
	confidence: float = 0.0


class OCRProcessResponseParsed(BaseModel):
	"""Parsed portion of the process response - matches frontend expectations"""
	date: Optional[str] = None
	supplier_name: Optional[str] = None
	invoice_number: Optional[str] = None
	document_type: Optional[str] = None
	currency: Optional[str] = None
	line_items: List[Dict[str, Any]] = []


class OCRProcessResponse(BaseModel):
	"""Response format expected by frontend DocumentImport.js"""
	ok: bool
	ocr: OCRProcessResponseOcr
	parsed: OCRProcessResponseParsed


def rebuild_models() -> None:
	OCRLine.model_rebuild()
	OCRResult.model_rebuild()
	OCRItemMatch.model_rebuild()
	OCRParsedItem.model_rebuild()
	OCRParsedDocument.model_rebuild()
	OCRCreateReceivingRequest.model_rebuild()
