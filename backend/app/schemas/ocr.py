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
