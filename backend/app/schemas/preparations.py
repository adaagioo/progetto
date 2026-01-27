# backend/app/schemas/preparations.py
from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class PreparationYield(BaseModel):
    """Yield information for a preparation"""
    value: float
    unit: str = "portions"


class PreparationShelfLife(BaseModel):
    """Shelf life information for a preparation"""
    value: int
    unit: str = "days"


class PreparationItem(BaseModel):
    """Item in a preparation - supports both frontend format (ingredientId) and canonical format (itemId)"""
    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(default="ingredient", description="Type: 'ingredient' or 'preparation'")
    itemId: Optional[str] = Field(default=None, description="ID of the ingredient or preparation")
    ingredientId: Optional[str] = Field(default=None, description="Alias for itemId (frontend compatibility)")
    name: Optional[str] = Field(default=None, description="Name of the ingredient or preparation")
    qty: float = Field(..., ge=0)
    unit: Optional[str] = Field(default=None, description="Unit of measure (optional)")

    @model_validator(mode="before")
    @classmethod
    def handle_ingredient_id(cls, data: Any) -> Any:
        """Sync ingredientId and itemId bidirectionally for frontend compatibility"""
        if isinstance(data, dict):
            # Input: if ingredientId provided, copy to itemId
            if "ingredientId" in data and "itemId" not in data:
                data["itemId"] = data["ingredientId"]
            # Output: if itemId exists but ingredientId doesn't, copy back
            elif "itemId" in data and "ingredientId" not in data:
                data["ingredientId"] = data["itemId"]
        return data


class PreparationCreate(BaseModel):
    """Create preparation - restaurantId is added from authenticated user"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1)
    portions: int = Field(default=1, ge=1)
    items: List[PreparationItem] = Field(default_factory=list)
    notes: Optional[str] = None
    yield_: Optional[PreparationYield] = Field(default=None, alias="yield")
    shelfLife: Optional[PreparationShelfLife] = None


class PreparationUpdate(BaseModel):
    """Update preparation"""
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    portions: Optional[int] = Field(None, ge=1)
    items: Optional[List[PreparationItem]] = None
    notes: Optional[str] = None
    yield_: Optional[PreparationYield] = Field(default=None, alias="yield")
    shelfLife: Optional[PreparationShelfLife] = None


class Preparation(BaseModel):
    """Preparation response model"""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    restaurantId: str
    portions: int
    items: List[PreparationItem] = []
    notes: Optional[str] = None
    yield_: Optional[PreparationYield] = Field(default=None, alias="yield")
    shelfLife: Optional[PreparationShelfLife] = None
    cost: Optional[float] = Field(None, description="Total cost for all portions")
    costPerPortion: Optional[float] = Field(None, description="Cost per single portion")
