# backend/app/repositories/files_repo.py
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from backend.app.db.mongo import get_db

def _col():
    return get_db()["files"]

async def insert_meta(meta: Dict[str, Any]) -> str:
    meta = {**meta, "createdAt": datetime.now(tz=timezone.utc)}
    res = await _col().insert_one(meta)
    return str(res.inserted_id)

async def get_meta(file_id: str, restaurant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get file metadata. If restaurant_id is provided, enforces multi-tenancy check."""
    query = {"_id": ObjectId(file_id)}
    if restaurant_id:
        query["restaurantId"] = restaurant_id
    return await _col().find_one(query)

async def delete_meta(file_id: str, restaurant_id: Optional[str] = None) -> bool:
    """Delete file metadata. If restaurant_id is provided, enforces multi-tenancy check."""
    query = {"_id": ObjectId(file_id)}
    if restaurant_id:
        query["restaurantId"] = restaurant_id
    res = await _col().delete_one(query)
    return res.deleted_count == 1

async def list_files(restaurant_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """List files. If restaurant_id is provided, filters by restaurant."""
    query = {}
    if restaurant_id:
        query["restaurantId"] = restaurant_id
    cur = _col().find(query).limit(limit)
    return [doc async for doc in cur]
