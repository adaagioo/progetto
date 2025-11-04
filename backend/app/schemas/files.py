# backend/app/schemas/files.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class FileUploadResponse(BaseModel):
	id: str
	filename: str
	contentType: Optional[str] = None
	length: int


class FileRef(BaseModel):
	id: str
	filename: str
