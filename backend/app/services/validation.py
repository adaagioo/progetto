# backend/app/services/validation.py
from __future__ import annotations
from typing import Iterable
from backend.app.repositories.ingredients_repo import find_one as find_ing
from backend.app.repositories.preparations_repo import find_one as find_prep

ALLOWED_TYPES = {"ingredient", "preparation"}


async def validate_items(restaurant_id: str, items: Iterable[dict]) -> None:
	for item in items or []:
		t = item.get("type")
		if t not in ALLOWED_TYPES:
			raise ValueError(f"Invalid item.type: {t!r}")
		qty = item.get("qty") or item.get("qtyPerPortion")
		if qty is None or qty < 0:
			raise ValueError("Quantity must be >= 0")
		ref_id = item.get("itemId")
		if not ref_id:
			raise ValueError("itemId is required")
		if t == "ingredient":
			if not await find_ing(restaurant_id, ref_id):
				raise ValueError(f"Referenced ingredient {ref_id} not found")
		elif t == "preparation":
			if not await find_prep(restaurant_id, ref_id):
				raise ValueError(f"Referenced preparation {ref_id} not found")
