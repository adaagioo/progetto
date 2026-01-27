# backend/app/schemas/suppliers.py
from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

from backend.app.schemas.files import FileRef


class SupplierBase(BaseModel):
	name: str = Field(..., min_length=1)
	email: Optional[str] = None
	phone: Optional[str] = None
	address: Optional[str] = None
	notes: Optional[str] = None
	active: bool = True
	contactName: Optional[str] = Field(None, description="Contact person name")


class SupplierCreate(SupplierBase):
	"""Create supplier - supports frontend 'contacts' object structure"""
	model_config = ConfigDict(populate_by_name=True)

	@model_validator(mode="before")
	@classmethod
	def flatten_contacts(cls, data: Any) -> Any:
		"""Extract fields from nested 'contacts' object for frontend compatibility"""
		if isinstance(data, dict) and "contacts" in data:
			contacts = data.pop("contacts")
			if isinstance(contacts, dict):
				if contacts.get("email") and not data.get("email"):
					data["email"] = contacts["email"]
				if contacts.get("phone") and not data.get("phone"):
					data["phone"] = contacts["phone"]
				if contacts.get("name") and not data.get("contactName"):
					data["contactName"] = contacts["name"]
		return data


class SupplierUpdate(BaseModel):
	"""Update supplier - supports frontend 'contacts' object structure"""
	model_config = ConfigDict(populate_by_name=True)

	name: Optional[str] = None
	email: Optional[str] = None
	phone: Optional[str] = None
	address: Optional[str] = None
	notes: Optional[str] = None
	active: Optional[bool] = None
	contactName: Optional[str] = None

	@model_validator(mode="before")
	@classmethod
	def flatten_contacts(cls, data: Any) -> Any:
		"""Extract fields from nested 'contacts' object for frontend compatibility"""
		if isinstance(data, dict) and "contacts" in data:
			contacts = data.pop("contacts")
			if isinstance(contacts, dict):
				if contacts.get("email") and not data.get("email"):
					data["email"] = contacts["email"]
				if contacts.get("phone") and not data.get("phone"):
					data["phone"] = contacts["phone"]
				if contacts.get("name") and not data.get("contactName"):
					data["contactName"] = contacts["name"]
		return data


class SupplierFull(SupplierBase):
	"""Full supplier data including restaurantId"""
	restaurantId: str


class Supplier(SupplierFull):
	id: str
	files: Optional[List[FileRef]] = None


class SupplierDependencies(BaseModel):
	supplierId: str
	hasReferences: bool
	references: dict  # {"inventoryDefaults": int, "receiving": int}
