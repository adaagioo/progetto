# backend/app/services/ocr_service.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from dataclasses import asdict
from pathlib import Path

from backend.app.schemas.ocr import OCRResult, OCRLine
from backend.app.core.config import settings
from backend.app.repositories.files_repo import get_meta
from backend.app.services.document_parser import parse_document
from backend.app.services.matching_service import suggest_inventory_matches

# NOTE: soft deps
try:
	import pytesseract
	from PIL import Image

	HAS_TESS = True
except Exception:
	HAS_TESS = False


# pdf -> images lazy import
def _pdf_to_images(pdf_path: str, max_pages: int) -> List["Image.Image"]:
	try:
		from pdf2image import convert_from_path
		imgs = convert_from_path(pdf_path, first_page=1, last_page=max_pages, dpi=300)
		return imgs
	except Exception:
		return []


def _read_file_bytes(path: str) -> bytes:
	return Path(path).read_bytes()


def _tesseract_available() -> bool:
	if not HAS_TESS:
		return False
	try:
		pytesseract.pytesseract.tesseract_cmd = getattr(settings, "TESSERACT_CMD", "tesseract")
		_ = pytesseract.get_tesseract_version()
		return True
	except Exception:
		return False


def _image_to_lines(img: "Image.Image", lang: str) -> List[Tuple[str, float]]:
	"""
	Uses image_to_data to extract text lines with confidence.
	Returns list[(text, conf)] for non-empty lines.
	"""
	from pytesseract import image_to_data
	import numpy as np

	data = image_to_data(img, lang=lang, output_type="dict")
	n = len(data.get("text", []))
	# group by line_num within a page
	lines: Dict[int, List[Tuple[str, float]]] = {}
	for i in range(n):
		txt = (data["text"][i] or "").strip()
		if not txt:
			continue
		conf_raw = data.get("conf", ["0"] * n)[i]
		try:
			conf = float(conf_raw)
		except Exception:
			conf = 0.0
		ln = int(data.get("line_num", [0] * n)[i] or 0)
		lines.setdefault(ln, []).append((txt, conf))

	out: List[Tuple[str, float]] = []
	for ln, chunks in sorted(lines.items(), key=lambda kv: kv[0]):
		text = " ".join(t for t, _ in chunks).strip()
		if not text:
			continue
		# average confidence
		conf = sum(c for _, c in chunks) / max(1, len(chunks))
		out.append((text, conf))
	return out


async def run_ocr(file_id: str, language: str) -> OCRResult:
	"""
	Orchestrates OCR on an uploaded file:
	- fetch meta from Mongo (files_repo)
	- detect content type (pdf vs image) via extension
	- run Tesseract if available & allowed; otherwise fallback to stub
	- always returns OCRResult with .lines and .meta
	"""
	# Validate language against whitelist
	lang = language or "eng"
	if getattr(settings, "OCR_LANG_WHITELIST", None):
		if lang not in settings.OCR_LANG_WHITELIST:
			# degrade to English if unknown
			lang = "eng"

	meta = await get_meta(file_id)
	if not meta:
		return OCRResult(ok=False, lines=[], meta={"error": "file_not_found", "engine": "none"})

	path = str(meta["path"])
	suffix = Path(path).suffix.lower()
	use_tess = (settings.OCR_ENGINE.lower() == "tesseract") and _tesseract_available()

	if not use_tess:
		# Safe stub, deterministic output
		lines = [
			OCRLine(text="OCR engine not available (stub)", confidence=0.0),
			OCRLine(text=f"fileId={file_id}", confidence=0.0),
			OCRLine(text=f"lang={lang}", confidence=0.0),
		]
		parsed = parse_document([l.text for l in lines])
		return OCRResult(ok=True, lines=lines, meta={
			"engine": "stub",
			"language": lang,
			"parsed": {
				"date": parsed.date,
				"supplier": parsed.supplier,
				"currency": parsed.currency,
				"items": [asdict(it) for it in parsed.items],
			}
		})

	# Real OCR
	images: List["Image.Image"] = []
	try:
		if suffix == ".pdf":
			images = _pdf_to_images(path, max_pages=getattr(settings, "OCR_MAX_PAGES", 5))
		else:
			raw = _read_file_bytes(path)
			from io import BytesIO
			images = [Image.open(BytesIO(raw)).convert("RGB")]
	except Exception as e:
		return OCRResult(ok=False, lines=[],
		                 meta={"engine": "tesseract", "language": lang, "error": f"load_failed: {e}"})

	if not images:
		return OCRResult(ok=False, lines=[], meta={"engine": "tesseract", "language": lang, "error": "no_images"})

	all_lines: List[OCRLine] = []
	pages = 0
	for img in images:
		pages += 1
		try:
			for text, conf in _image_to_lines(img, lang=lang):
				if text:
					# normalize confidence to 0..1
					c = max(0.0, min(1.0, conf / 100.0))
					all_lines.append(OCRLine(text=text, confidence=c))
		except Exception as e:
			# continue but record partial failure
			all_lines.append(OCRLine(text=f"[OCR error on page {pages}: {e}]", confidence=0.0))

	# Parsed structure (best-effort; never fatal)
	parsed = parse_document([l.text for l in all_lines])

	matched_items = []
	for it in parsed.items:
		try:
			suggestions = await suggest_inventory_matches(it.name, max_results=5)
		except Exception:
			suggestions = []
		matched_items.append({
			"name": it.name,
			"qty": it.qty,
			"unit": it.unit,
			"unitCost": it.unitCost,
			"matches": suggestions,
		})

	return OCRResult(ok=True, lines=all_lines, meta={
		"engine": "tesseract" if use_tess else "stub",
		"language": lang,
		"pages": pages if use_tess else None,
		"parsed": {
			"date": parsed.date,
			"supplier": parsed.supplier,
			"currency": parsed.currency,
			"items": matched_items,
		}
	})
