# backend/app/services/matching_service.py
from __future__ import annotations
from typing import List, Dict, Any
from difflib import SequenceMatcher
from backend.app.utils.text_norm import normalize_text
from backend.app.repositories.inventory_repo import find_candidates_by_name


def _similarity(a: str, b: str) -> float:
	a = normalize_text(a)
	b = normalize_text(b)
	if not a or not b:
		return 0.0
	return SequenceMatcher(None, a, b).ratio()  # 0..1


def _best_name(doc: Dict[str, Any]) -> str:
	name = doc.get("name") or ""
	return name


async def suggest_inventory_matches(item_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
	candidates = await find_candidates_by_name(item_name, limit=max_results)
	scored = []
	for doc in candidates:
		name = _best_name(doc)
		score = _similarity(item_name, name)
		in_tokens_match = normalize_text(item_name).split(" ")[0:1] == normalize_text(name).split(" ")[0:1]
		if in_tokens_match:
			score = min(1.0, score + 0.05)
		scored.append({
			"inventoryId": str(doc.get("_id")),
			"name": name,
			"score": round(float(score), 4),
		})
	scored.sort(key=lambda x: x["score"], reverse=True)
	return scored[:max_results]
