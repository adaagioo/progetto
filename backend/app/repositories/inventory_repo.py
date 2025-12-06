# backend/app/repositories/inventory_repo.py
from __future__ import annotations
from typing import Optional, Any, List
from bson import ObjectId  # type: ignore
from backend.app.db.mongo import get_db
from typing import Dict, Any
from datetime import datetime, timedelta, date, timezone
from bson import ObjectId as _ObjectId

from backend.app.utils.text_norm import tokenize


def _col():
	return get_db()["inventory"]


def _as_id(doc: dict) -> dict:
	if not doc:
		return doc
	doc["id"] = str(doc.pop("_id"))
	return doc


async def find_by_id(restaurant_id: str, inv_id: str) -> Optional[dict]:
	return _as_id(await _col().find_one({"_id": ObjectId(inv_id), "restaurantId": restaurant_id}))


async def find_by_ingredient_id(restaurant_id: str, ingredient_id: str) -> Optional[dict]:
	"""Find inventory by ingredientId and restaurantId"""
	return _as_id(await _col().find_one({"ingredientId": ingredient_id, "restaurantId": restaurant_id}))


async def find_all(restaurant_id: str) -> List[dict]:
	cur = _col().find({"restaurantId": restaurant_id})
	return [_as_id(d) async for d in cur]


async def insert_one(doc: dict) -> str:
	res = await _col().insert_one(doc)
	return str(res.inserted_id)


async def delete_by_receiving(restaurant_id: str, receiving_id: str) -> int:
	res = await _col().delete_many({"restaurantId": restaurant_id, "receivingId": receiving_id})
	return res.deleted_count


def _recipes():
	return get_db()["recipes"]


def _preps():
	return get_db()["preparations"]


async def aggregate_valuation_summary(as_of: date) -> Dict[str, Any]:
	pipeline = [
		{"$project": {
			"category": {"$ifNull": ["$category", "nofood"]},
			"value": {"$multiply": [{"$ifNull": ["$quantity", 0]}, {"$ifNull": ["$unitCost", 0]}]}
		}},
		{"$group": {"_id": "$category", "total": {"$sum": "$value"}, "count": {"$sum": 1}}},
	]
	totals = {"food": 0.0, "beverage": 0.0, "nofood": 0.0}
	item_count = 0
	async for g in _col().aggregate(pipeline):
		cat = (g.get("_id") or "nofood")
		count = g.get("count", 0)
		item_count += count
		if cat not in totals:
			totals["nofood"] += float(g.get("total", 0.0))
		else:
			totals[cat] = float(g.get("total", 0.0))
	grand = totals["food"] + totals["beverage"] + totals["nofood"]
	return {
		"asOf": as_of,
		"total": grand,
		"categories": totals,
		"itemCount": item_count
	}


async def aggregate_valuation_by_category(as_of: date) -> list[dict]:
	pipeline = [
		{"$project": {
			"category": {"$ifNull": ["$category", "other"]},
			"value": {"$multiply": [{"$ifNull": ["$quantity", 0]}, {"$ifNull": ["$unitCost", 0]}]}
		}},
		{"$group": {"_id": "$category", "total": {"$sum": "$value"}}},
		{"$sort": {"_id": 1}},
	]
	out: list[dict] = []
	async for g in _col().aggregate(pipeline):
		out.append({"category": g.get("_id") or "other", "total": float(g.get("total", 0.0))})
	return out


async def find_expiring_inventory_items(days: int) -> list[dict]:
	now = datetime.now(tz=timezone.utc)
	up_to = now + timedelta(days=days)
	cursor = _col().find({"expiryDate": {"$gte": now, "$lte": up_to}}, projection={"name": 1, "expiryDate": 1}).sort(
		[("expiryDate", 1)])
	out: list[dict] = []
	async for doc in cursor:
		eid = str(doc.get("_id"))
		exp = doc.get("expiryDate")
		days_left = (exp - now).days if exp else 0
		out.append({"id": eid, "name": doc.get("name", ""), "expiryDate": exp, "daysLeft": days_left})
	return out


async def apply_inventory_adjustments(items: list[dict], actor_id: str | None) -> tuple[bool, int, int]:
	ok, processed, failed = True, 0, 0
	col = _col()
	adj_col = get_db()["inventory_adjustments"]
	for it in items:
		try:
			inv_id = _ObjectId(it["inventoryId"])
			delta = float(it["delta"])
			reason = str(it.get("reason", ""))
			res = await col.update_one({"_id": inv_id}, {"$inc": {"quantity": delta}})
			if res.matched_count != 1:
				failed += 1
				ok = False
				continue
			await adj_col.insert_one({
				"inventoryId": inv_id,
				"delta": delta,
				"reason": reason,
				"actorId": actor_id,
				"at": datetime.now(tz=timezone.utc),
			})
			processed += 1
		except Exception:
			failed += 1
			ok = False
	return ok, processed, failed


async def lookup_inventory_dependencies(inventory_id: str) -> Dict[str, Any]:
	inv_id = _ObjectId(inventory_id)
	rq = {"ingredients.inventoryId": inv_id}
	recipe_ids = [str(d["_id"]) async for d in _recipes().find(rq, projection={"_id": 1}).limit(500)]
	prep_ids = [str(d["_id"]) async for d in _preps().find(rq, projection={"_id": 1}).limit(500)]
	return {
		"inventoryId": inventory_id,
		"recipesUsing": len(recipe_ids),
		"preparationsUsing": len(prep_ids),
		"recipeIds": recipe_ids,
		"preparationIds": prep_ids,
	}


async def bulk_update_inventory(items: list[dict]) -> tuple[bool, int, int]:
	ok, processed, failed = True, 0, 0
	col = _col()
	for it in items:
		try:
			inv_id = _ObjectId(it["inventoryId"])
			patch = {}
			for k in ("reorderLevel", "targetLevel", "unit", "defaultSupplierId", "name"):
				if it.get(k) is not None:
					patch[k] = it[k]
			if not patch:
				processed += 1
				continue
			res = await col.update_one({"_id": inv_id}, {"$set": patch})
			if res.matched_count != 1:
				ok = False
				failed += 1
			else:
				processed += 1
		except Exception:
			ok = False
			failed += 1
	return ok, processed, failed


def _regex_all_tokens(tokens: List[str]) -> Dict[str, Any]:
	ors = []
	for tk in tokens:
		ors.append({
			"$or": [
				{"name": {"$regex": tk, "$options": "i"}},
				{"aliases": {"$elemMatch": {"$regex": tk, "$options": "i"}}},
			]
		})
	return {"$and": ors} if ors else {}


async def find_candidates_by_name(name: str, limit: int = 8) -> List[Dict[str, Any]]:
	col = _col()
	tokens = tokenize(name)
	if not tokens:
		return []
	q = _regex_all_tokens(tokens)
	docs = await col.find(q, {"name": 1, "aliases": 1}).limit(limit * 3).to_list(length=limit * 3)
	if not docs:
		q = {"$or": [{"name": {"$regex": tk, "$options": "i"}}
		             for tk in tokens]}
		docs = await col.find(q, {"name": 1, "aliases": 1}).limit(limit * 3).to_list(length=limit * 3)
	return docs[: limit * 3]
