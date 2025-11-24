# backend/app/schemas/menu.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class MenuItemCreate(BaseModel):
	"""Create menu item request"""
	refType: str  # 'ingredient', 'preparation', or 'recipe'
	refId: str  # ID of the ingredient/preparation/recipe
	displayName: Optional[str] = None  # Optional override for display name
	price: Optional[float] = None  # Optional selling price override (major units)
	tags: Optional[List[str]] = []  # Tags like 'special', 'seasonal', etc.
	isActive: bool = True


class MenuItemUpdate(BaseModel):
	"""Update menu item request"""
	displayName: Optional[str] = None
	price: Optional[float] = None
	tags: Optional[List[str]] = None
	isActive: Optional[bool] = None


class MenuItem(BaseModel):
	"""Menu item model"""
	model_config = ConfigDict(extra="ignore")
	id: str
	menuId: str
	refType: str  # 'ingredient', 'preparation', or 'recipe'
	refId: str
	displayName: Optional[str] = None
	price: Optional[float] = None  # Selling price in major units (EUR)
	tags: List[str] = []
	isActive: bool = True
	# Populated fields (from referenced entity)
	name: Optional[str] = None  # Canonical name from ref entity
	category: Optional[str] = None  # Category from ref entity
	recipeType: Optional[str] = None  # kitchen/bar for recipes
	computedCost: Optional[float] = None  # Cost per portion
	allergens: Optional[List[str]] = []
	otherAllergens: Optional[List[str]] = []
	availabilityStatus: Optional[str] = "unknown"  # available, low, out
	feasiblePortions: Optional[int] = 0
	createdAt: str
	updatedAt: Optional[str] = None


class MenuCreate(BaseModel):
	"""Create menu request"""
	name: str
	description: Optional[str] = None
	effectiveFrom: str  # ISO date
	effectiveTo: Optional[str] = None  # ISO date
	isActive: bool = True


class MenuUpdate(BaseModel):
	"""Update menu request"""
	name: Optional[str] = None
	description: Optional[str] = None
	effectiveFrom: Optional[str] = None
	effectiveTo: Optional[str] = None
	isActive: Optional[bool] = None


class Menu(BaseModel):
	"""Menu model"""
	model_config = ConfigDict(extra="ignore")
	id: str
	restaurantId: str
	name: str
	description: Optional[str] = None
	effectiveFrom: str
	effectiveTo: Optional[str] = None
	isActive: bool = True
	createdAt: str
	updatedAt: Optional[str] = None
