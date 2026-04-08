# backend/app/schemas/recipes.py
from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class RecipeShelfLife(BaseModel):
    """Shelf life information for a recipe"""
    value: int
    unit: str = "days"


class RecipeItem(BaseModel):
    """Item in a recipe (ingredient or preparation)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "ingredient",
            "itemId": "507f1f77bcf86cd799439011",
            "qtyPerPortion": 0.25
        }
    })

    type: str = Field(default="ingredient", description="Type: 'ingredient' or 'preparation'")
    itemId: str = Field(..., description="ID of the ingredient or preparation")
    qtyPerPortion: float = Field(..., ge=0, description="Quantity per portion")
    unit: Optional[str] = Field(default=None, description="Unit of measure (optional)")


class RecipeCreate(BaseModel):
    """Create a new recipe - restaurantId is added from authenticated user"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, description="Recipe name")
    portions: int = Field(1, ge=1, description="Number of portions this recipe makes")
    items: List[RecipeItem] = Field(default_factory=list, description="List of ingredients/preparations")
    notes: Optional[str] = Field(None, description="Additional notes or instructions")
    sellingPrice: Optional[float] = Field(None, ge=0, description="Selling price per portion (minor units)")
    vatPct: Optional[float] = Field(default=22.0, ge=0, le=100, description="VAT percentage (default 22%)")
    # Additional fields from frontend
    category: Optional[str] = Field(None, description="Recipe category (e.g., 'antipasti', 'primi')")
    recipeType: Optional[str] = Field(default="kitchen", description="Recipe type: 'kitchen' or 'bar'")
    targetFoodCostPct: Optional[float] = Field(None, ge=0, le=100, description="Target food cost percentage")
    shelfLife: Optional[RecipeShelfLife] = Field(None, description="Shelf life information")

    @model_validator(mode="before")
    @classmethod
    def handle_price_alias(cls, data: Any) -> Any:
        """Map 'price' to 'sellingPrice' for frontend compatibility"""
        if isinstance(data, dict):
            if "price" in data and "sellingPrice" not in data:
                data["sellingPrice"] = data.pop("price")
        return data


class RecipeUpdate(BaseModel):
    """Update an existing recipe"""
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, description="Recipe name")
    portions: Optional[int] = Field(None, ge=1, description="Number of portions")
    items: Optional[List[RecipeItem]] = Field(None, description="List of ingredients/preparations")
    notes: Optional[str] = Field(None, description="Additional notes")
    sellingPrice: Optional[float] = Field(None, ge=0, description="Selling price per portion (minor units)")
    vatPct: Optional[float] = Field(None, ge=0, le=100, description="VAT percentage")
    # Additional fields from frontend
    category: Optional[str] = Field(None, description="Recipe category")
    recipeType: Optional[str] = Field(None, description="Recipe type: 'kitchen' or 'bar'")
    targetFoodCostPct: Optional[float] = Field(None, ge=0, le=100, description="Target food cost percentage")
    shelfLife: Optional[RecipeShelfLife] = Field(None, description="Shelf life information")

    @model_validator(mode="before")
    @classmethod
    def handle_price_alias(cls, data: Any) -> Any:
        """Map 'price' to 'sellingPrice' for frontend compatibility"""
        if isinstance(data, dict):
            if "price" in data and "sellingPrice" not in data:
                data["sellingPrice"] = data.pop("price")
        return data


class Recipe(BaseModel):
    """Recipe with calculated cost fields"""
    model_config = ConfigDict(populate_by_name=True, json_schema_extra={
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
    price: Optional[float] = Field(None, description="Alias for sellingPrice (frontend)")
    priceWithoutVat: Optional[float] = Field(None, description="Price without VAT")
    foodCostPct: Optional[float] = Field(None, description="Food cost percentage (cost/price * 100)")
    vatPct: Optional[float] = Field(default=22.0, description="VAT percentage")
    # Additional fields from frontend
    category: Optional[str] = Field(None, description="Recipe category")
    recipeType: Optional[str] = Field(default="kitchen", description="Recipe type: 'kitchen' or 'bar'")
    targetFoodCostPct: Optional[float] = Field(None, description="Target food cost percentage")
    shelfLife: Optional[RecipeShelfLife] = Field(None, description="Shelf life information")

    @model_validator(mode="before")
    @classmethod
    def sync_price_fields(cls, data: Any) -> Any:
        """Sync price and sellingPrice bidirectionally"""
        if isinstance(data, dict):
            if "sellingPrice" in data and "price" not in data:
                data["price"] = data["sellingPrice"]
            elif "price" in data and "sellingPrice" not in data:
                data["sellingPrice"] = data["price"]
        return data
