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
	fileType: Optional[str] = None

	@property
	def id(self) -> str:
		"""Alias for fileId - frontend expects 'id'"""
		return self.fileId

	def model_dump(self, **kwargs) -> dict:
		"""Include 'id' in serialization for frontend compatibility"""
		data = super().model_dump(**kwargs)
		data["id"] = self.fileId
		return data
