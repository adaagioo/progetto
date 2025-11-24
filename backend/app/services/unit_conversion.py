# backend/app/services/unit_conversion.py
from __future__ import annotations

_CONV = {
	("g", "kg"): 1 / 1000.0,
	("kg", "g"): 1000.0,
	("ml", "l"): 1 / 1000.0,
	("l", "ml"): 1000.0,
	("pcs", "pcs"): 1.0,
	("pc", "pcs"): 1.0,
	("piece", "pcs"): 1.0,
	("pieces", "pcs"): 1.0,
	# Imperial/US to metric (approx)
	("oz", "g"): 28.3495,
	("lb", "kg"): 0.453592,
	("g", "oz"): 1 / 28.3495,
	("kg", "lb"): 1 / 0.453592,
	# Volume kitchen
	("tsp", "ml"): 5.0,
	("tbsp", "ml"): 15.0,
	("cup", "ml"): 240.0,
	("ml", "tsp"): 1 / 5.0,
	("ml", "tbsp"): 1 / 15.0,
	("ml", "cup"): 1 / 240.0,
}


def _norm(u: str | None) -> str | None:
	if u is None:
		return None
	u = u.strip().lower()
	if u in ("pc", "piece", "pieces"):
		return "pcs"
	if u in ("ounce", "ounces"):
		return "oz"
	if u in ("pound", "pounds"):
		return "lb"
	return u


def can_convert(from_unit: str | None, to_unit: str | None) -> bool:
	f = _norm(from_unit)
	t = _norm(to_unit)
	if f is None or t is None:
		return False
	return (f, t) in _CONV or (f == t)


def convert_quantity(value: float, from_unit: str | None, to_unit: str | None) -> float:
	f = _norm(from_unit)
	t = _norm(to_unit)
	if value == 0:
		return 0.0
	if f is None or t is None:
		# If units not set, assume same
		return float(value)
	if f == t:
		return float(value)
	factor = _CONV.get((f, t))
	if factor is None:
		# No known conversion, return original (caller should handle)
		return float(value)
	return float(value) * factor
