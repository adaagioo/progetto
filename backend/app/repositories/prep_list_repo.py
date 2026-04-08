# backend/app/repositories/prep_list_repo.py
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from backend.app.db.mongo import get_db
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def _col():
    return get_db()["prep_lists"]


def _as_id(doc: dict) -> dict:
    """Convert MongoDB _id to id field"""
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc


async def save_prep_list(restaurant_id: str, prep_date: date, items: List[Dict[str, Any]]) -> str:
    """
    Save or update a prep list for a specific date.
    Uses upsert to replace existing list for the same date.

    Args:
        restaurant_id: Restaurant ID
        prep_date: Date for the prep list
        items: List of prep items with quantities, notes, etc.

    Returns:
        ID of the saved/updated document
    """
    date_str = prep_date.isoformat() if isinstance(prep_date, date) else prep_date

    doc = {
        "restaurantId": restaurant_id,
        "date": date_str,
        "items": items,
        "updatedAt": datetime.now(tz=timezone.utc),
    }

    # Upsert: update if exists, insert if not
    result = await _col().update_one(
        {"restaurantId": restaurant_id, "date": date_str},
        {"$set": doc, "$setOnInsert": {"createdAt": datetime.now(tz=timezone.utc)}},
        upsert=True
    )

    if result.upserted_id:
        logger.info(f"Created new prep list for {date_str}")
        return str(result.upserted_id)
    else:
        # Find the existing document to return its ID
        existing = await _col().find_one({"restaurantId": restaurant_id, "date": date_str})
        logger.info(f"Updated existing prep list for {date_str}")
        return str(existing["_id"]) if existing else ""


async def get_prep_list(restaurant_id: str, prep_date: date) -> Optional[Dict[str, Any]]:
    """
    Get a saved prep list for a specific date.

    Args:
        restaurant_id: Restaurant ID
        prep_date: Date to retrieve

    Returns:
        Prep list document or None if not found
    """
    date_str = prep_date.isoformat() if isinstance(prep_date, date) else prep_date
    doc = await _col().find_one({"restaurantId": restaurant_id, "date": date_str})
    return _as_id(doc) if doc else None


async def list_prep_lists(restaurant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all saved prep lists for a restaurant.

    Args:
        restaurant_id: Restaurant ID
        limit: Maximum number of lists to return

    Returns:
        List of prep list documents, sorted by date descending
    """
    cursor = _col().find({"restaurantId": restaurant_id}).sort("date", -1).limit(limit)
    return [_as_id(doc) async for doc in cursor]


async def delete_prep_list(restaurant_id: str, prep_date: date) -> bool:
    """
    Delete a prep list for a specific date.

    Args:
        restaurant_id: Restaurant ID
        prep_date: Date to delete

    Returns:
        True if deleted, False if not found
    """
    date_str = prep_date.isoformat() if isinstance(prep_date, date) else prep_date
    result = await _col().delete_one({"restaurantId": restaurant_id, "date": date_str})
    return result.deleted_count > 0
