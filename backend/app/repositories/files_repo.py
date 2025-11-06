# backend/app/repositories/files_repo.py
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson import ObjectId
from backend.app.db.mongo import get_db

def _col():
    return get_db()["files"]

async def insert_meta(meta: Dict[str, Any]) -> str:
    meta = {**meta, "createdAt": datetime.utcnow()}
    res = await _col().insert_one(meta)
    return str(res.inserted_id)

async def get_meta(file_id: str) -> Optional[Dict[str, Any]]:
    return await _col().find_one({"_id": ObjectId(file_id)})

async def delete_meta(file_id: str) -> bool:
    res = await _col().delete_one({"_id": ObjectId(file_id)})
    return res.deleted_count == 1

async def list_files(limit: int = 200) -> List[Dict[str, Any]]:
    cur = _col().find({}).limit(limit)
    return [doc async for doc in cur]
