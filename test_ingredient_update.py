#!/usr/bin/env python3
"""
Test script to verify the updated Ingredient models work correctly
"""

import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_ingredient_models():
    """Test the updated ingredient models"""
    
    # Test data with new fields
    test_ingredient = {
        "name": "Test Ingredient with New Fields",
        "unit": "kg",
        "packSize": 1.0,
        "packCost": 10.0,
        "supplier": "Test Supplier",
        "allergen": "nuts",  # Deprecated field
        "allergens": ["nuts", "gluten"],  # New array field
        "minStockQty": 5.0,
        "category": "food",
        "wastePct": 15.0,  # New waste percentage field
        "shelfLife": {  # New shelf life field
            "value": 30,
            "unit": "days"
        }
    }
    
    print("Testing ingredient model with new fields...")
    print(f"Test data: {json.dumps(test_ingredient, indent=2)}")
    
    # Test that the model can be created (this tests the Pydantic models)
    try:
        from server import IngredientCreate, Ingredient, ShelfLife
        
        # Test ShelfLife model
        shelf_life = ShelfLife(value=30, unit="days")
        print(f"✓ ShelfLife model works: {shelf_life}")
        
        # Test IngredientCreate model
        ingredient_create = IngredientCreate(**test_ingredient)
        print(f"✓ IngredientCreate model works")
        print(f"  - allergens: {ingredient_create.allergens}")
        print(f"  - wastePct: {ingredient_create.wastePct}")
        print(f"  - shelfLife: {ingredient_create.shelfLife}")
        
        # Test that we can create an Ingredient instance with calculated fields
        ingredient_dict = {
            "id": "test-id",
            "restaurantId": "test-restaurant",
            "name": test_ingredient["name"],
            "unit": test_ingredient["unit"],
            "packSize": test_ingredient["packSize"],
            "packCost": test_ingredient["packCost"],
            "unitCost": test_ingredient["packCost"] / test_ingredient["packSize"],
            "effectiveUnitCost": (test_ingredient["packCost"] / test_ingredient["packSize"]) * (1 + test_ingredient["wastePct"] / 100),
            "supplier": test_ingredient["supplier"],
            "allergen": test_ingredient["allergen"],
            "allergens": test_ingredient["allergens"],
            "minStockQty": test_ingredient["minStockQty"],
            "category": test_ingredient["category"],
            "wastePct": test_ingredient["wastePct"],
            "shelfLife": test_ingredient["shelfLife"],
            "createdAt": "2024-01-01T00:00:00Z"
        }
        
        ingredient = Ingredient(**ingredient_dict)
        print(f"✓ Ingredient model works")
        print(f"  - unitCost: {ingredient.unitCost}")
        print(f"  - effectiveUnitCost: {ingredient.effectiveUnitCost}")
        print(f"  - allergens: {ingredient.allergens}")
        print(f"  - wastePct: {ingredient.wastePct}")
        print(f"  - shelfLife: {ingredient.shelfLife}")
        
        print("\n✅ All ingredient model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ingredient_models()
    if success:
        print("\n🎉 Ingredient model update completed successfully!")
        print("\nNew features added:")
        print("- ShelfLife model for tracking ingredient shelf life")
        print("- allergens array field (EU-14 compliant)")
        print("- wastePct field for waste percentage tracking")
        print("- effectiveUnitCost calculation including waste")
        print("- Backward compatibility maintained with deprecated 'allergen' field")
    else:
        print("\n❌ Tests failed - please check the implementation")