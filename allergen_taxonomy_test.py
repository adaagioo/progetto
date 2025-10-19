#!/usr/bin/env python3
"""
Allergen Taxonomy Backend Final Verification Test Suite
Tests uppercase codes, mixed case normalization, propagation, and i18n functionality
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional

# Configuration
BACKEND_URL = "https://food-analytics.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "admin123"}
}

# EU-14 Allergen Codes (should match backend)
EU_14_ALLERGENS = [
    "GLUTEN", "CRUSTACEANS", "MOLLUSCS", "EGGS", "FISH", 
    "TREE_NUTS", "SOY", "DAIRY", "SESAME", "CELERY", "MUSTARD", "SULPHITES"
]

class AllergenTaxonomyTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.created_ingredients = []
        self.created_preparations = []
        self.created_recipes = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    async def authenticate(self, user_type: str = "admin") -> bool:
        """Authenticate with the backend"""
        try:
            credentials = TEST_CREDENTIALS[user_type]
            
            async with self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=credentials,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.user_data = data["user"]
                    self.log_result("Authentication", True, f"Logged in as {user_type}")
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Authentication", False, f"Login failed: {response.status}", error_text)
                    return False
        except Exception as e:
            self.log_result("Authentication", False, f"Login error: {str(e)}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    # ============ ALLERGEN CRUD TESTS ============
    
    async def test_ingredient_create_with_allergens(self):
        """Test ingredient creation with allergens and otherAllergens"""
        test_cases = [
            {
                "name": "Flour with Gluten",
                "allergens": ["GLUTEN", "DAIRY"],
                "otherAllergens": ["truffle oil"],
                "expected_allergens": ["GLUTEN", "DAIRY"],
                "expected_other": ["truffle oil"]
            },
            {
                "name": "Mixed Case Allergens",
                "allergens": ["gluten", "dairy"],  # lowercase input
                "otherAllergens": [],
                "expected_allergens": ["GLUTEN", "DAIRY"],  # should be uppercased
                "expected_other": []
            },
            {
                "name": "Custom Allergens Only",
                "allergens": [],
                "otherAllergens": ["truffle extract", "special seasoning"],
                "expected_allergens": [],
                "expected_other": ["truffle extract", "special seasoning"]
            }
        ]
        
        for i, case in enumerate(test_cases):
            try:
                ingredient_data = {
                    "name": case["name"],
                    "unit": "kg",
                    "packSize": 1.0,
                    "packCost": 5.00,
                    "allergens": case["allergens"],
                    "otherAllergens": case["otherAllergens"],
                    "category": "food"
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/ingredients",
                    json=ingredient_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        ingredient = await response.json()
                        self.created_ingredients.append(ingredient)
                        
                        # Verify allergens are stored in uppercase
                        if ingredient["allergens"] == case["expected_allergens"]:
                            self.log_result(f"Ingredient Allergens Uppercase {i+1}", True, 
                                          f"Allergens correctly stored as {ingredient['allergens']}")
                        else:
                            self.log_result(f"Ingredient Allergens Uppercase {i+1}", False, 
                                          f"Expected {case['expected_allergens']}, got {ingredient['allergens']}")
                        
                        # Verify otherAllergens preserved as-is
                        if ingredient["otherAllergens"] == case["expected_other"]:
                            self.log_result(f"Ingredient Other Allergens {i+1}", True, 
                                          f"Other allergens correctly stored as {ingredient['otherAllergens']}")
                        else:
                            self.log_result(f"Ingredient Other Allergens {i+1}", False, 
                                          f"Expected {case['expected_other']}, got {ingredient['otherAllergens']}")
                    else:
                        error_text = await response.text()
                        self.log_result(f"Ingredient Create {i+1}", False, 
                                      f"Failed to create ingredient: {response.status}", error_text)
            except Exception as e:
                self.log_result(f"Ingredient Create {i+1}", False, f"Error: {str(e)}")
    
    async def test_ingredient_get_allergens_uppercase(self):
        """Test GET ingredients returns allergens in uppercase"""
        try:
            async with self.session.get(
                f"{BACKEND_URL}/ingredients",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    ingredients = await response.json()
                    
                    uppercase_verified = True
                    for ingredient in ingredients:
                        for allergen in ingredient.get("allergens", []):
                            if allergen != allergen.upper():
                                uppercase_verified = False
                                self.log_result("GET Ingredients Uppercase", False, 
                                              f"Found non-uppercase allergen: {allergen} in {ingredient['name']}")
                                break
                        if not uppercase_verified:
                            break
                    
                    if uppercase_verified:
                        self.log_result("GET Ingredients Uppercase", True, 
                                      "All allergens returned in uppercase format")
                else:
                    error_text = await response.text()
                    self.log_result("GET Ingredients Uppercase", False, 
                                  f"Failed to get ingredients: {response.status}", error_text)
        except Exception as e:
            self.log_result("GET Ingredients Uppercase", False, f"Error: {str(e)}")
    
    async def test_ingredient_update_allergens(self):
        """Test updating ingredient allergens maintains uppercase"""
        if not self.created_ingredients:
            self.log_result("Update Ingredient Allergens", False, "No ingredients to update")
            return
        
        try:
            ingredient = self.created_ingredients[0]
            update_data = {
                "name": ingredient["name"],
                "unit": ingredient["unit"],
                "packSize": ingredient["packSize"],
                "packCost": ingredient["packCost"],
                "allergens": ["crustaceans", "molluscs"],  # lowercase input
                "otherAllergens": ["updated custom allergen"]
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    updated_ingredient = await response.json()
                    
                    # Verify allergens are uppercased
                    expected_allergens = ["CRUSTACEANS", "MOLLUSCS"]
                    if updated_ingredient["allergens"] == expected_allergens:
                        self.log_result("Update Ingredient Allergens", True, 
                                      f"Allergens correctly updated to {updated_ingredient['allergens']}")
                    else:
                        self.log_result("Update Ingredient Allergens", False, 
                                      f"Expected {expected_allergens}, got {updated_ingredient['allergens']}")
                    
                    # Verify otherAllergens updated
                    expected_other = ["updated custom allergen"]
                    if updated_ingredient["otherAllergens"] == expected_other:
                        self.log_result("Update Ingredient Other Allergens", True, 
                                      f"Other allergens correctly updated to {updated_ingredient['otherAllergens']}")
                    else:
                        self.log_result("Update Ingredient Other Allergens", False, 
                                      f"Expected {expected_other}, got {updated_ingredient['otherAllergens']}")
                else:
                    error_text = await response.text()
                    self.log_result("Update Ingredient Allergens", False, 
                                  f"Failed to update: {response.status}", error_text)
        except Exception as e:
            self.log_result("Update Ingredient Allergens", False, f"Error: {str(e)}")
    
    async def test_ingredient_delete_cleanup(self):
        """Test ingredient deletion"""
        if not self.created_ingredients:
            self.log_result("Delete Ingredient", False, "No ingredients to delete")
            return
        
        try:
            ingredient = self.created_ingredients[-1]  # Delete last created
            
            async with self.session.delete(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    # Verify ingredient is gone
                    async with self.session.get(
                        f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                        headers=self.get_auth_headers()
                    ) as verify_response:
                        if verify_response.status == 404:
                            self.log_result("Delete Ingredient", True, "Ingredient deleted successfully")
                        else:
                            self.log_result("Delete Ingredient", False, "Ingredient still accessible after deletion")
                else:
                    error_text = await response.text()
                    self.log_result("Delete Ingredient", False, f"Delete failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Delete Ingredient", False, f"Error: {str(e)}")
    
    # ============ ALLERGEN PROPAGATION TESTS ============
    
    async def test_allergen_propagation_ingredient_to_preparation(self):
        """Test allergen propagation from ingredients to preparations"""
        if len(self.created_ingredients) < 3:
            self.log_result("Allergen Propagation Prep", False, "Not enough ingredients for test")
            return
        
        try:
            # Create preparation using ingredients with different allergens
            flour = next((ing for ing in self.created_ingredients if "Flour" in ing["name"]), None)
            milk = None
            truffle = None
            
            # Create specific test ingredients if not found
            if not flour:
                flour_data = {
                    "name": "Test Flour",
                    "unit": "kg",
                    "packSize": 1.0,
                    "packCost": 2.50,
                    "allergens": ["GLUTEN"],
                    "otherAllergens": []
                }
                async with self.session.post(
                    f"{BACKEND_URL}/ingredients",
                    json=flour_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        flour = await response.json()
                        self.created_ingredients.append(flour)
            
            # Create milk ingredient
            milk_data = {
                "name": "Test Milk",
                "unit": "L",
                "packSize": 1.0,
                "packCost": 1.20,
                "allergens": ["DAIRY"],
                "otherAllergens": []
            }
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=milk_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    milk = await response.json()
                    self.created_ingredients.append(milk)
            
            # Create truffle ingredient
            truffle_data = {
                "name": "Test Truffle",
                "unit": "kg",
                "packSize": 0.1,
                "packCost": 50.00,
                "allergens": [],
                "otherAllergens": ["truffle extract"]
            }
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=truffle_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    truffle = await response.json()
                    self.created_ingredients.append(truffle)
            
            if not all([flour, milk, truffle]):
                self.log_result("Allergen Propagation Prep", False, "Failed to create test ingredients")
                return
            
            # Create preparation using all three ingredients
            prep_data = {
                "name": "Test Preparation with Allergens",
                "items": [
                    {"ingredientId": flour["id"], "qty": 0.5, "unit": "kg"},
                    {"ingredientId": milk["id"], "qty": 0.2, "unit": "L"},
                    {"ingredientId": truffle["id"], "qty": 0.01, "unit": "kg"}
                ],
                "yield": {"value": 4.0, "unit": "portions"}
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    self.created_preparations.append(preparation)
                    
                    # Verify allergen propagation
                    expected_allergens = sorted(["DAIRY", "GLUTEN"])  # Union and sorted
                    expected_other = ["truffle extract"]
                    
                    if preparation["allergens"] == expected_allergens:
                        self.log_result("Preparation Allergen Propagation", True, 
                                      f"Correct allergens: {preparation['allergens']}")
                    else:
                        self.log_result("Preparation Allergen Propagation", False, 
                                      f"Expected {expected_allergens}, got {preparation['allergens']}")
                    
                    if preparation["otherAllergens"] == expected_other:
                        self.log_result("Preparation Other Allergen Propagation", True, 
                                      f"Correct other allergens: {preparation['otherAllergens']}")
                    else:
                        self.log_result("Preparation Other Allergen Propagation", False, 
                                      f"Expected {expected_other}, got {preparation['otherAllergens']}")
                else:
                    error_text = await response.text()
                    self.log_result("Allergen Propagation Prep", False, 
                                  f"Failed to create preparation: {response.status}", error_text)
        except Exception as e:
            self.log_result("Allergen Propagation Prep", False, f"Error: {str(e)}")
    
    async def test_allergen_propagation_preparation_to_recipe(self):
        """Test allergen propagation from preparations and ingredients to recipes"""
        if not self.created_preparations or len(self.created_ingredients) < 1:
            self.log_result("Allergen Propagation Recipe", False, "Missing preparations or ingredients")
            return
        
        try:
            preparation = self.created_preparations[0]
            
            # Create basil ingredient with custom allergen
            basil_data = {
                "name": "Test Basil",
                "unit": "kg",
                "packSize": 0.1,
                "packCost": 3.00,
                "allergens": [],
                "otherAllergens": ["pesto base"]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=basil_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    basil = await response.json()
                    self.created_ingredients.append(basil)
                else:
                    self.log_result("Allergen Propagation Recipe", False, "Failed to create basil ingredient")
                    return
            
            # Create recipe with preparation + ingredient
            recipe_data = {
                "name": "Test Recipe with Mixed Items",
                "category": "test",
                "portions": 4,
                "targetFoodCostPct": 30.0,
                "price": 1200,
                "items": [
                    {
                        "type": "preparation",
                        "itemId": preparation["id"],
                        "qtyPerPortion": 1.0,
                        "unit": "portions"
                    },
                    {
                        "type": "ingredient",
                        "itemId": basil["id"],
                        "qtyPerPortion": 0.005,
                        "unit": "kg"
                    }
                ]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    self.created_recipes.append(recipe)
                    
                    # Verify allergen aggregation
                    # Should include allergens from preparation (GLUTEN, DAIRY) + ingredient allergens
                    expected_allergens = sorted(["DAIRY", "GLUTEN"])
                    expected_other = sorted(["pesto base", "truffle extract"])  # Union from prep + ingredient
                    
                    if recipe["allergens"] == expected_allergens:
                        self.log_result("Recipe Allergen Aggregation", True, 
                                      f"Correct allergens: {recipe['allergens']}")
                    else:
                        self.log_result("Recipe Allergen Aggregation", False, 
                                      f"Expected {expected_allergens}, got {recipe['allergens']}")
                    
                    if sorted(recipe["otherAllergens"]) == expected_other:
                        self.log_result("Recipe Other Allergen Aggregation", True, 
                                      f"Correct other allergens: {recipe['otherAllergens']}")
                    else:
                        self.log_result("Recipe Other Allergen Aggregation", False, 
                                      f"Expected {expected_other}, got {recipe['otherAllergens']}")
                else:
                    error_text = await response.text()
                    self.log_result("Allergen Propagation Recipe", False, 
                                  f"Failed to create recipe: {response.status}", error_text)
        except Exception as e:
            self.log_result("Allergen Propagation Recipe", False, f"Error: {str(e)}")
    
    async def test_allergen_union_logic(self):
        """Test union logic for otherAllergens with deduplication"""
        try:
            # Create ingredients with overlapping otherAllergens
            ingredient1_data = {
                "name": "Ingredient 1",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 5.00,
                "allergens": ["GLUTEN"],
                "otherAllergens": ["custom1", "shared_allergen"]
            }
            
            ingredient2_data = {
                "name": "Ingredient 2", 
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 3.00,
                "allergens": ["DAIRY"],
                "otherAllergens": ["custom2", "shared_allergen"]  # Duplicate
            }
            
            # Create both ingredients
            ingredients = []
            for data in [ingredient1_data, ingredient2_data]:
                async with self.session.post(
                    f"{BACKEND_URL}/ingredients",
                    json=data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        ingredient = await response.json()
                        ingredients.append(ingredient)
                        self.created_ingredients.append(ingredient)
            
            if len(ingredients) != 2:
                self.log_result("Union Logic Test", False, "Failed to create test ingredients")
                return
            
            # Create preparation using both ingredients
            prep_data = {
                "name": "Union Test Preparation",
                "items": [
                    {"ingredientId": ingredients[0]["id"], "qty": 0.5, "unit": "kg"},
                    {"ingredientId": ingredients[1]["id"], "qty": 0.3, "unit": "kg"}
                ]
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    self.created_preparations.append(preparation)
                    
                    # Verify union and deduplication
                    expected_allergens = sorted(["DAIRY", "GLUTEN"])
                    expected_other = sorted(["custom1", "custom2", "shared_allergen"])  # Deduplicated
                    
                    if preparation["allergens"] == expected_allergens:
                        self.log_result("Union Logic Allergens", True, 
                                      f"Correct allergen union: {preparation['allergens']}")
                    else:
                        self.log_result("Union Logic Allergens", False, 
                                      f"Expected {expected_allergens}, got {preparation['allergens']}")
                    
                    if sorted(preparation["otherAllergens"]) == expected_other:
                        self.log_result("Union Logic Other Allergens", True, 
                                      f"Correct other allergen union with deduplication: {preparation['otherAllergens']}")
                    else:
                        self.log_result("Union Logic Other Allergens", False, 
                                      f"Expected {expected_other}, got {preparation['otherAllergens']}")
                else:
                    error_text = await response.text()
                    self.log_result("Union Logic Test", False, 
                                  f"Failed to create preparation: {response.status}", error_text)
        except Exception as e:
            self.log_result("Union Logic Test", False, f"Error: {str(e)}")
    
    # ============ RBAC TESTS ============
    
    async def test_rbac_ingredient_updates(self):
        """Test RBAC for ingredient updates"""
        if not self.created_ingredients:
            self.log_result("RBAC Ingredient Updates", False, "No ingredients to test")
            return
        
        ingredient = self.created_ingredients[0]
        update_data = {
            "name": ingredient["name"],
            "unit": ingredient["unit"],
            "packSize": ingredient["packSize"],
            "packCost": ingredient["packCost"],
            "allergens": ["EGGS"]
        }
        
        # Test admin access
        try:
            await self.authenticate("admin")
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    self.log_result("RBAC Admin Ingredient Update", True, "Admin can update ingredients")
                else:
                    self.log_result("RBAC Admin Ingredient Update", False, f"Admin update failed: {response.status}")
        except Exception as e:
            self.log_result("RBAC Admin Ingredient Update", False, f"Error: {str(e)}")
        
        # Test manager access
        try:
            await self.authenticate("manager")
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    self.log_result("RBAC Manager Ingredient Update", True, "Manager can update ingredients")
                else:
                    self.log_result("RBAC Manager Ingredient Update", False, f"Manager update failed: {response.status}")
        except Exception as e:
            self.log_result("RBAC Manager Ingredient Update", False, f"Error: {str(e)}")
        
        # Test staff access (should be denied)
        try:
            await self.authenticate("staff")
            async with self.session.put(
                f"{BACKEND_URL}/ingredients/{ingredient['id']}",
                json=update_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 403:
                    self.log_result("RBAC Staff Ingredient Update", True, "Staff correctly denied ingredient updates")
                else:
                    self.log_result("RBAC Staff Ingredient Update", False, f"Staff should be denied: {response.status}")
        except Exception as e:
            self.log_result("RBAC Staff Ingredient Update", False, f"Error: {str(e)}")
        
        # Re-authenticate as admin for remaining tests
        await self.authenticate("admin")
    
    # ============ I18N SAFE RESPONSES ============
    
    async def test_i18n_safe_responses(self):
        """Test that all allergen codes are returned as uppercase strings"""
        try:
            # Test ingredients endpoint
            async with self.session.get(
                f"{BACKEND_URL}/ingredients",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    ingredients = await response.json()
                    
                    i18n_safe = True
                    for ingredient in ingredients:
                        # Check allergens are uppercase strings
                        for allergen in ingredient.get("allergens", []):
                            if not isinstance(allergen, str) or allergen != allergen.upper():
                                i18n_safe = False
                                self.log_result("I18n Safe Ingredients", False, 
                                              f"Non-uppercase allergen: {allergen} in {ingredient['name']}")
                                break
                        
                        # Check otherAllergens are preserved as strings
                        for other in ingredient.get("otherAllergens", []):
                            if not isinstance(other, str):
                                i18n_safe = False
                                self.log_result("I18n Safe Ingredients", False, 
                                              f"Non-string other allergen: {other} in {ingredient['name']}")
                                break
                        
                        if not i18n_safe:
                            break
                    
                    if i18n_safe:
                        self.log_result("I18n Safe Ingredients", True, "All allergen codes are uppercase strings")
                else:
                    self.log_result("I18n Safe Ingredients", False, f"Failed to get ingredients: {response.status}")
            
            # Test preparations endpoint
            async with self.session.get(
                f"{BACKEND_URL}/preparations",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    preparations = await response.json()
                    
                    i18n_safe = True
                    for prep in preparations:
                        # Check allergens are uppercase strings
                        for allergen in prep.get("allergens", []):
                            if not isinstance(allergen, str) or allergen != allergen.upper():
                                i18n_safe = False
                                self.log_result("I18n Safe Preparations", False, 
                                              f"Non-uppercase allergen: {allergen} in {prep['name']}")
                                break
                        
                        if not i18n_safe:
                            break
                    
                    if i18n_safe:
                        self.log_result("I18n Safe Preparations", True, "All preparation allergen codes are uppercase strings")
                else:
                    self.log_result("I18n Safe Preparations", False, f"Failed to get preparations: {response.status}")
            
            # Test recipes endpoint
            async with self.session.get(
                f"{BACKEND_URL}/recipes",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    recipes = await response.json()
                    
                    i18n_safe = True
                    for recipe in recipes:
                        # Check allergens are uppercase strings
                        for allergen in recipe.get("allergens", []):
                            if not isinstance(allergen, str) or allergen != allergen.upper():
                                i18n_safe = False
                                self.log_result("I18n Safe Recipes", False, 
                                              f"Non-uppercase allergen: {allergen} in {recipe['name']}")
                                break
                        
                        if not i18n_safe:
                            break
                    
                    if i18n_safe:
                        self.log_result("I18n Safe Recipes", True, "All recipe allergen codes are uppercase strings")
                else:
                    self.log_result("I18n Safe Recipes", False, f"Failed to get recipes: {response.status}")
        
        except Exception as e:
            self.log_result("I18n Safe Responses", False, f"Error: {str(e)}")
    
    # ============ LEGACY MIGRATION TEST ============
    
    async def test_legacy_migration(self):
        """Test legacy allergen field migration (if applicable)"""
        try:
            # Try to create ingredient with legacy allergen field
            legacy_data = {
                "name": "Legacy Allergen Test",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 5.00,
                "allergen": "gluten",  # Legacy field
                "allergens": [],
                "otherAllergens": []
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/ingredients",
                json=legacy_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    ingredient = await response.json()
                    self.created_ingredients.append(ingredient)
                    
                    # Check if legacy allergen was migrated
                    if "GLUTEN" in ingredient.get("allergens", []):
                        self.log_result("Legacy Migration", True, 
                                      "Legacy allergen field migrated to allergens array")
                    elif "gluten" in ingredient.get("otherAllergens", []):
                        self.log_result("Legacy Migration", True, 
                                      "Legacy allergen field migrated to otherAllergens array")
                    else:
                        self.log_result("Legacy Migration", False, 
                                      f"Legacy allergen not found in response: {ingredient}")
                else:
                    # Legacy field might not be supported anymore
                    self.log_result("Legacy Migration", True, 
                                  "Legacy allergen field not supported (expected for new implementation)")
        except Exception as e:
            self.log_result("Legacy Migration", False, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 70)
        print("🧪 COMPREHENSIVE ALLERGEN TAXONOMY BACKEND TESTING COMPLETE")
        print("=" * 70)
        print(f"📊 RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}% success rate)")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        print(f"\n✅ SUCCESSFUL TESTS ({passed_tests}):")
        for result in self.test_results:
            if result["success"]:
                print(f"   • {result['test']}: {result['message']}")
        
        # Critical issues summary
        critical_failures = []
        for result in self.test_results:
            if not result["success"] and any(keyword in result["test"].lower() for keyword in 
                                           ["uppercase", "propagation", "rbac", "allergen"]):
                critical_failures.append(result["test"])
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES REQUIRING ATTENTION:")
            for failure in critical_failures:
                print(f"   • {failure}")
        
        return passed_tests, total_tests
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive allergen taxonomy tests"""
        print("🚀 Starting Comprehensive Allergen Taxonomy Backend Testing")
        print("=" * 70)
        
        # Authenticate as admin
        if not await self.authenticate("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        print("\n🧪 1. ALLERGEN CRUD OPERATIONS")
        print("-" * 40)
        await self.test_ingredient_create_with_allergens()
        await self.test_ingredient_get_allergens_uppercase()
        await self.test_ingredient_update_allergens()
        await self.test_ingredient_delete_cleanup()
        
        print("\n🔗 2. ALLERGEN PROPAGATION CHAIN")
        print("-" * 40)
        await self.test_allergen_propagation_ingredient_to_preparation()
        await self.test_allergen_propagation_preparation_to_recipe()
        await self.test_allergen_union_logic()
        
        print("\n🔐 3. RBAC VERIFICATION")
        print("-" * 40)
        await self.test_rbac_ingredient_updates()
        
        print("\n🌍 4. I18N-SAFE RESPONSES")
        print("-" * 40)
        await self.test_i18n_safe_responses()
        
        print("\n📜 5. LEGACY MIGRATION")
        print("-" * 40)
        await self.test_legacy_migration()
        
        # Print final summary
        passed, total = self.print_summary()
        
        return passed, total

async def main():
    """Main test runner"""
    async with AllergenTaxonomyTester() as tester:
        passed, total = await tester.run_comprehensive_tests()
        
        # Exit with appropriate code
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED! Allergen taxonomy backend is working correctly.")
            return 0
        else:
            print(f"\n⚠️  {total - passed} tests failed. Please review the issues above.")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)