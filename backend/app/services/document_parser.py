# backend/app/services/document_parser.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

DATE_PATTERNS = [
	r"date[:\s]*([0-3]?\d[/-][01]?\d[/-]\d{2,4})",
	r"data[:\s]*([0-3]?\d[./-][01]?\d[./-]\d{2,4})",
	r"(\d{4}-[01]\d-[0-3]\d)",  # ISO
]
CURRENCY_HINTS = [r"€", r"eur", r"euro", r"\$", "usd"]

ITEM_LINE_PATTERNS = [
	# es: "Pomodori 3 kg x 2.40"
	r"^(?P<name>.+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|l|ml|pz)\s*(?:x|×)\s*(?P<unitCost>\d+(?:[.,]\d+))\b",
	# es: "Farina 1 kg 1.20"
	r"^(?P<name>.+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|l|ml|pz)\s+(?P<unitCost>\d+(?:[.,]\d+))\b",
]


@dataclass
class ParsedItem:
	name: str
	qty: float
	unit: str
	unitCost: float


@dataclass
class ParsedDocument:
	date: Optional[str]
	supplier: Optional[str]
	currency: Optional[str]
	items: List[ParsedItem]


def _norm_num(s: str) -> float:
	# support both "1.200,50" and "1200.50" – quick heuristic
	s = s.strip()
	if "," in s and "." in s:
		# assume EU format: 1.234,56 -> 1234.56
		s = s.replace(".", "").replace(",", ".")
	else:
		s = s.replace(",", ".")
	try:
		return float(s)
	except ValueError:
		return 0.0


def _guess_currency(text: str) -> Optional[str]:
	lower = text.lower()
	if any(re.search(h, lower) for h in CURRENCY_HINTS):
		return "EUR" if "€" in text or "eur" in lower or "euro" in lower else "USD" if "$" in text or "usd" in lower else None
	return None


def _extract_date(text: str) -> Optional[str]:
	lower = text.lower()
	for pat in DATE_PATTERNS:
		m = re.search(pat, lower, flags=re.IGNORECASE)
		if not m:
			continue
		raw = m.group(1)
		for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y"):
			try:
				dt = datetime.strptime(raw, fmt)
				return dt.strftime("%Y-%m-%d")
			except ValueError:
				continue
	return None


def _extract_supplier(lines: List[str]) -> Optional[str]:
	head = "\n".join(lines[:6])
	chunks = [ln for ln in head.splitlines() if not re.fullmatch(r"[\s\-_=*#]+", ln.strip())]
	for i, ln in enumerate(chunks):
		if re.search(r"\b(vat|p\.?iva|partita\s+iva)\b", ln, flags=re.IGNORECASE):
			if i > 0 and chunks[i - 1].strip():
				return chunks[i - 1].strip()[:120]
	for ln in chunks:
		if ln.strip():
			return ln.strip()[:120]
	return None


def _extract_items(lines: List[str]) -> List[ParsedItem]:
	out: List[ParsedItem] = []
	for ln in lines:
		s = ln.strip()
		if not s:
			continue
		for pat in ITEM_LINE_PATTERNS:
			m = re.match(pat, s, flags=re.IGNORECASE)
			if m:
				name = m.group("name").strip()
				qty = _norm_num(m.group("qty"))
				unit = m.group("unit").lower()
				unit_cost = _norm_num(m.group("unitCost"))
				if re.search(r"\b(total|totale|iva|subtotal)\b", name, flags=re.IGNORECASE):
					continue
				out.append(ParsedItem(name=name, qty=qty, unit=unit, unitCost=unit_cost))
				break
	return out


def parse_document(ocr_lines: List[str]) -> ParsedDocument:
	text = "\n".join(ocr_lines)
	date = _extract_date(text)
	currency = _guess_currency(text) or "EUR"
	supplier = _extract_supplier(ocr_lines) or None
	items = _extract_items(ocr_lines)
	return ParsedDocument(
		date=date,
		supplier=supplier,
		currency=currency,
		items=items,
	)
