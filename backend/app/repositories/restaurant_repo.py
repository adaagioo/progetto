# backend/app/repositories/restaurant_repo.py
from __future__ import annotations
from typing import Optional, Any
from backend.app.db.mongo import get_db


def _col():
    return get_db()["restaurants"]


def _as_dict(doc: dict) -> dict:
    if not doc:
        return doc
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def find_by_id(restaurant_id: str) -> Optional[dict]:
    """Find restaurant by its string ID field (not ObjectId)"""
    doc = await _col().find_one({"id": restaurant_id})
    return _as_dict(doc)


async def upsert(restaurant_id: str, data: dict) -> dict:
    """Update or create restaurant document"""
    await _col().update_one(
        {"id": restaurant_id},
        {"$set": {**data, "id": restaurant_id}},
        upsert=True
    )
    return await find_by_id(restaurant_id)


async def create(restaurant_id: str, data: dict) -> dict:
    """Create a new restaurant"""
    doc = {**data, "id": restaurant_id}
    await _col().insert_one(doc)
    return _as_dict(doc)
