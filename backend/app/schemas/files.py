# backend/app/schemas/files.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class FileMeta(BaseModel):
	id: str
	filename: str
	contentType: Optional[str] = None
	size: int
	path: str
	ownerId: Optional[str] = None
	createdAt: str


class FileRef(BaseModel):
	fileId: str
	filename: str
	contentType: Optional[str] = None
	size: int
	path: str
	url: str
