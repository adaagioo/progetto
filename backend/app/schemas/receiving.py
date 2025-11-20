# backend/app/schemas/receiving.py
from __future__ import annotations
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, field_serializer, ConfigDict

from backend.app.schemas.files import FileRef


class ReceivingItem(BaseModel):
	# Use frontend field names directly
	ingredientId: str
	qty: float = Field(ge=0)
	unit: Optional[str] = None
	unitPrice: Optional[float] = None
	supplierId: Optional[str] = None
	notes: Optional[str] = None
	description: Optional[str] = None
	packFormat: Optional[str] = None
	expiryDate: Optional[date] = None

	@field_serializer('expiryDate')
	def serialize_expiry_date(self, value: Optional[date]) -> Optional[str]:
		return value.isoformat() if value else None


class ReceivingPost(BaseModel):
	# Accept both frontend and backend field names
	arrivedAt: date
	lines: List[ReceivingItem]
	supplierId: Optional[str] = None
	category: Optional[str] = None
	notes: Optional[str] = None


class ReceivingUpdate(BaseModel):
	arrivedAt: Optional[date] = None
	lines: Optional[List[ReceivingItem]] = None
	supplierId: Optional[str] = None
	category: Optional[str] = None
	notes: Optional[str] = None


class Receiving(BaseModel):
	model_config = ConfigDict(
		populate_by_name=True,
		json_schema_serialization_defaults_required=True
	)

	id: str
	arrivedAt: date = Field(validation_alias="date", serialization_alias="arrivedAt")
	lines: List[ReceivingItem] = Field(validation_alias="items", serialization_alias="lines")
	createdAt: str
	supplierId: Optional[str] = None
	category: Optional[str] = None
	notes: Optional[str] = None
	files: Optional[List[FileRef]] = None

	@field_serializer('arrivedAt')
	def serialize_date(self, value: date) -> str:
		return value.isoformat()
