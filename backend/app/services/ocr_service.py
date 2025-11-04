# backend/app/services/ocr_service.py
from __future__ import annotations
from typing import List, Dict, Any
from backend.app.schemas.ocr import OCRResult, OCRLine


# TODO (af):
# Safe stub: placeholder OCR — returns a deterministic response for now.
# Later you can integrate real OCR (e.g., Tesseract or cloud service).
async def run_ocr(file_id: str, language: str) -> OCRResult:
	# For safety and determinism, we don't read the file here.
	lines = [
		OCRLine(text="OCR not yet implemented", confidence=0.0),
		OCRLine(text=f"fileId={file_id}", confidence=0.0),
		OCRLine(text=f"lang={language}", confidence=0.0),
	]
	return OCRResult(ok=True, lines=lines, meta={"engine": "stub"})
