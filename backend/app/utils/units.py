# backend/app/utils/units.py
from __future__ import annotations

_BASE = {
	# massa -> grams
	"g": 1.0, "kg": 1000.0, "mg": 0.001, "lb": 453.592, "oz": 28.3495,
	# volume -> litri
	"ml": 0.001, "l": 1.0, "cl": 0.01, "dl": 0.1, "cup": 0.236588, "tbsp": 0.0147868, "tsp": 0.00492892,
	# pezzi (no conversion)
	"pcs": 1.0, "unit": 1.0, "piece": 1.0,
}


def normalize_quantity_to_base_unit(qty: float, from_unit: str, to_unit: str) -> float:
	fu = (from_unit or "").lower().strip()
	tu = (to_unit or "").lower().strip()
	if fu not in _BASE or tu not in _BASE:
		raise ValueError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")
	return qty * (_BASE[fu] / _BASE[tu])
