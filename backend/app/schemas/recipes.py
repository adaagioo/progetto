# backend/app/schemas/recipes.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class RecipeItem(BaseModel):
    """Item in a recipe (ingredient or preparation)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "ingredient",
            "itemId": "507f1f77bcf86cd799439011",
            "qtyPerPortion": 0.25
        }
    })

    type: str = Field(..., description="Type: 'ingredient' or 'preparation'")
    itemId: str = Field(..., description="ID of the ingredient or preparation")
    qtyPerPortion: float = Field(..., ge=0, description="Quantity per portion")

class RecipeCreate(BaseModel):
    """Create a new recipe"""
    name: str = Field(..., min_length=1, description="Recipe name")
    restaurantId: str = Field(..., description="Restaurant ID")
    portions: int = Field(1, ge=1, description="Number of portions this recipe makes")
    items: List[RecipeItem] = Field(default_factory=list, description="List of ingredients/preparations")
    notes: Optional[str] = Field(None, description="Additional notes or instructions")
    sellingPrice: Optional[float] = Field(None, ge=0, description="Selling price per portion")
    vatPct: Optional[float] = Field(default=22.0, ge=0, le=100, description="VAT percentage (default 22%)")

class RecipeUpdate(BaseModel):
    """Update an existing recipe"""
    name: Optional[str] = Field(None, description="Recipe name")
    portions: Optional[int] = Field(None, ge=1, description="Number of portions")
    items: Optional[List[RecipeItem]] = Field(None, description="List of ingredients/preparations")
    notes: Optional[str] = Field(None, description="Additional notes")
    sellingPrice: Optional[float] = Field(None, ge=0, description="Selling price per portion")
    vatPct: Optional[float] = Field(None, ge=0, le=100, description="VAT percentage")

class Recipe(BaseModel):
    """Recipe with calculated cost fields"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "507f1f77bcf86cd799439011",
            "name": "Margherita Pizza",
            "restaurantId": "507f191e810c19729de860ea",
            "portions": 1,
            "items": [
                {"type": "ingredient", "itemId": "ing123", "qtyPerPortion": 0.25}
            ],
            "totalCost": 3.50,
            "costPerPortion": 3.50,
            "sellingPrice": 8.00,
            "priceWithoutVat": 6.56,
            "foodCostPct": 43.75,
            "vatPct": 22.0
        }
    })

    id: str
    name: str
    restaurantId: str
    portions: int
    items: List[RecipeItem] = []
    notes: Optional[str] = None
    totalCost: Optional[float] = Field(None, description="Total cost for all portions")
    costPerPortion: Optional[float] = Field(None, description="Cost per single portion")
    sellingPrice: Optional[float] = Field(None, description="Selling price per portion")
    priceWithoutVat: Optional[float] = Field(None, description="Price without VAT")
    foodCostPct: Optional[float] = Field(None, description="Food cost percentage (cost/price * 100)")
    vatPct: Optional[float] = Field(default=22.0, description="VAT percentage")
