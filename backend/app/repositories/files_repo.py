# backend/app/repositories/files_repo.py
from __future__ import annotations
from typing import Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from backend.app.db.mongo import get_db


def _bucket() -> AsyncIOMotorGridFSBucket:
	return AsyncIOMotorGridFSBucket(get_db())


async def save_stream(filename: str, content_type: Optional[str], stream) -> Tuple[str, int]:
	bucket = _bucket()
	file_id = await bucket.upload_from_stream(filename, stream, metadata={"contentType": content_type})
	# gridfs does not directly return length; we can fetch it:
	file_doc = await get_db()["fs.files"].find_one({"_id": file_id})
	length = int(file_doc.get("length", 0)) if file_doc else 0
	return str(file_id), length


async def open_download_stream(file_id: str):
	return await _bucket().open_download_stream(ObjectId(file_id))


async def find_file_meta(file_id: str):
	return await get_db()["fs.files"].find_one({"_id": ObjectId(file_id)})
