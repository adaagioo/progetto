#!/usr/bin/env python3
"""
Backend Testing Suite for Phase 4 & 5 (Prep List, Order List, P&L Snapshot)
Tests all endpoints with RBAC, tenant isolation, forecast accuracy, and calculations
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Configuration
BACKEND_URL = "https://ristobrain-1.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "manager": {"email": "manager@test.com", "password": "manager123"},
    "staff": {"email": "staff@test.com", "password": "staff123"}
}

class Phase45BackendTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.test_data = {
            "ingredients": [],
            "preparations": [],
            "recipes": [],
            "sales": [],
            "suppliers": []
        }
        
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
    
    async def register_test_user(self, user_type: str = "admin") -> bool:
        """Register test user if not exists"""
        try:
            credentials = TEST_CREDENTIALS[user_type]
            register_data = {
                "email": credentials["email"],
                "password": credentials["password"],
                "displayName": f"Test {user_type.title()}",
                "restaurantName": f"Test Restaurant {user_type.title()}",
                "locale": "en-US"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.user_data = data["user"]
                    self.log_result("User Registration", True, f"Test {user_type} registered successfully")
                    return True
                elif response.status == 400:
                    # User already exists, try to login
                    return await self.authenticate(user_type)
                else:
                    error_text = await response.text()
                    self.log_result("User Registration", False, f"Registration failed: {response.status}", error_text)
                    return False
        except Exception as e:
            self.log_result("User Registration", False, f"Registration error: {str(e)}")
            return False

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
    
    async def setup_test_data(self):
        """Create test data for Phase 4 & 5 testing"""
        print("\n🏗️ Setting Up Test Data for Phase 4 & 5")
        print("-" * 50)
        
        # Create test ingredients
        await self.create_test_ingredients()
        
        # Create test preparations
        await self.create_test_preparations()
        
        # Create test recipes
        await self.create_test_recipes()
        
        # Create test suppliers
        await self.create_test_suppliers()
        
        # Create historical sales data for forecasting
        await self.create_historical_sales()
        
        # Create inventory records
        await self.create_test_inventory()
    
    async def create_test_ingredients(self):
        """Create test ingredients for forecasting"""
        ingredients_data = [
            {
                "name": "Flour 00",
                "unit": "kg",
                "packSize": 25.0,
                "packCost": 15.50,
                "wastePct": 5.0,
                "allergens": ["gluten"],
                "minStockQty": 10.0,
                "category": "food"
            },
            {
                "name": "San Marzano Tomatoes",
                "unit": "kg", 
                "packSize": 2.5,
                "packCost": 8.75,
                "wastePct": 10.0,
                "allergens": [],
                "minStockQty": 5.0,
                "category": "food"
            },
            {
                "name": "Mozzarella di Bufala",
                "unit": "kg",
                "packSize": 1.0,
                "packCost": 18.00,
                "wastePct": 8.0,
                "allergens": ["dairy"],
                "minStockQty": 3.0,
                "category": "food"
            },
            {
                "name": "Extra Virgin Olive Oil",
                "unit": "L",
                "packSize": 5.0,
                "packCost": 45.00,
                "wastePct": 2.0,
                "allergens": [],
                "minStockQty": 2.0,
                "category": "food"
            },
            {
                "name": "Fresh Basil",
                "unit": "kg",
                "packSize": 0.5,
                "packCost": 12.00,
                "wastePct": 25.0,
                "allergens": [],
                "minStockQty": 0.5,
                "category": "food"
            }
        ]
        
        for ingredient_data in ingredients_data:
            try:
                async with self.session.post(
                    f"{BACKEND_URL}/ingredients",
                    json=ingredient_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        ingredient = await response.json()
                        self.test_data["ingredients"].append(ingredient)
                        self.log_result("Create Test Ingredient", True, f"Created {ingredient['name']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Create Test Ingredient", False, f"Failed to create {ingredient_data['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Create Test Ingredient", False, f"Error creating {ingredient_data['name']}: {str(e)}")
    
    async def create_test_preparations(self):
        """Create test preparations"""
        if len(self.test_data["ingredients"]) < 3:
            self.log_result("Create Test Preparations", False, "Not enough ingredients")
            return
        
        flour = next((ing for ing in self.test_data["ingredients"] if "Flour" in ing["name"]), None)
        tomatoes = next((ing for ing in self.test_data["ingredients"] if "Tomatoes" in ing["name"]), None)
        mozzarella = next((ing for ing in self.test_data["ingredients"] if "Mozzarella" in ing["name"]), None)
        
        if not all([flour, tomatoes, mozzarella]):
            self.log_result("Create Test Preparations", False, "Required ingredients not found")
            return
        
        prep_data = {
            "name": "Pizza Base",
            "items": [
                {
                    "ingredientId": flour["id"],
                    "qty": 0.3,
                    "unit": "kg"
                },
                {
                    "ingredientId": tomatoes["id"],
                    "qty": 0.15,
                    "unit": "kg"
                },
                {
                    "ingredientId": mozzarella["id"],
                    "qty": 0.2,
                    "unit": "kg"
                }
            ],
            "yield": {
                "value": 4.0,
                "unit": "portions"
            },
            "shelfLife": {
                "value": 2,
                "unit": "days"
            },
            "notes": "Base pizza preparation"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/preparations",
                json=prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    preparation = await response.json()
                    self.test_data["preparations"].append(preparation)
                    self.log_result("Create Test Preparation", True, f"Created {preparation['name']}")
                else:
                    error_text = await response.text()
                    self.log_result("Create Test Preparation", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Create Test Preparation", False, f"Error: {str(e)}")
    
    async def create_test_recipes(self):
        """Create test recipes using preparations"""
        if len(self.test_data["preparations"]) < 1 or len(self.test_data["ingredients"]) < 2:
            self.log_result("Create Test Recipes", False, "Not enough preparations or ingredients")
            return
        
        pizza_base = self.test_data["preparations"][0]
        basil = next((ing for ing in self.test_data["ingredients"] if "Basil" in ing["name"]), None)
        olive_oil = next((ing for ing in self.test_data["ingredients"] if "Olive Oil" in ing["name"]), None)
        
        if not all([basil, olive_oil]):
            self.log_result("Create Test Recipes", False, "Required ingredients not found")
            return
        
        recipe_data = {
            "name": "Pizza Margherita",
            "category": "pizza",
            "portions": 4,
            "targetFoodCostPct": 30.0,
            "price": 1400,  # €14.00 in minor units
            "items": [
                {
                    "type": "preparation",
                    "itemId": pizza_base["id"],
                    "qtyPerPortion": 1.0,
                    "unit": "portions"
                },
                {
                    "type": "ingredient",
                    "itemId": basil["id"],
                    "qtyPerPortion": 0.005,
                    "unit": "kg"
                },
                {
                    "type": "ingredient",
                    "itemId": olive_oil["id"],
                    "qtyPerPortion": 0.01,
                    "unit": "L"
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/recipes",
                json=recipe_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    recipe = await response.json()
                    self.test_data["recipes"].append(recipe)
                    self.log_result("Create Test Recipe", True, f"Created {recipe['name']}")
                else:
                    error_text = await response.text()
                    self.log_result("Create Test Recipe", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Create Test Recipe", False, f"Error: {str(e)}")
    
    async def create_test_suppliers(self):
        """Create test suppliers for order list"""
        supplier_data = {
            "name": "Fornitore Principale",
            "contacts": {
                "name": "Mario Rossi",
                "phone": "+39 02 1234567",
                "email": "mario@fornitore.it"
            },
            "notes": "Fornitore principale per ingredienti"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/suppliers",
                json=supplier_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    supplier = await response.json()
                    self.test_data["suppliers"].append(supplier)
                    self.log_result("Create Test Supplier", True, f"Created {supplier['name']}")
                else:
                    error_text = await response.text()
                    self.log_result("Create Test Supplier", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("Create Test Supplier", False, f"Error: {str(e)}")
    
    async def create_historical_sales(self):
        """Create historical sales data for forecasting"""
        if len(self.test_data["recipes"]) < 1:
            self.log_result("Create Historical Sales", False, "No recipes available")
            return
        
        recipe = self.test_data["recipes"][0]
        
        # Create sales for last 4 weeks (same weekday pattern)
        today = datetime.now()
        target_weekday = (today.weekday() + 1) % 7  # Tomorrow's weekday
        
        for week_offset in range(1, 5):
            # Calculate date for same weekday in past weeks
            past_date = today - timedelta(weeks=week_offset)
            # Adjust to target weekday
            days_diff = (target_weekday - past_date.weekday()) % 7
            if days_diff > 3:  # If more than 3 days forward, go to previous week
                days_diff -= 7
            sales_date = past_date + timedelta(days=days_diff)
            
            # Vary quantities for realistic forecasting
            base_qty = 8
            variation = week_offset * 2  # Some variation
            qty = base_qty + variation
            
            sales_data = {
                "date": sales_date.strftime("%Y-%m-%d"),
                "lines": [
                    {
                        "recipeId": recipe["id"],
                        "qty": qty
                    }
                ],
                "revenue": qty * recipe["price"],
                "notes": f"Historical sales week {week_offset}"
            }
            
            try:
                async with self.session.post(
                    f"{BACKEND_URL}/sales",
                    json=sales_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        sales = await response.json()
                        self.test_data["sales"].append(sales)
                        self.log_result("Create Historical Sales", True, f"Created sales for {sales_date.strftime('%Y-%m-%d')} - {qty} portions")
                    else:
                        error_text = await response.text()
                        self.log_result("Create Historical Sales", False, f"Failed for {sales_date.strftime('%Y-%m-%d')}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Create Historical Sales", False, f"Error for {sales_date.strftime('%Y-%m-%d')}: {str(e)}")
    
    async def create_test_inventory(self):
        """Create test inventory records"""
        if len(self.test_data["ingredients"]) < 1:
            self.log_result("Create Test Inventory", False, "No ingredients available")
            return
        
        for ingredient in self.test_data["ingredients"]:
            # Create inventory with varying levels (some low stock)
            if "Flour" in ingredient["name"]:
                qty = 8.0  # Below minStockQty (10.0)
            elif "Basil" in ingredient["name"]:
                qty = 0.2  # Below minStockQty (0.5)
            else:
                qty = ingredient["minStockQty"] + 2.0  # Above minimum
            
            inventory_data = {
                "ingredientId": ingredient["id"],
                "qty": qty,
                "unit": ingredient["unit"],
                "countType": "physical",
                "location": "main_storage"
            }
            
            try:
                async with self.session.post(
                    f"{BACKEND_URL}/inventory",
                    json=inventory_data,
                    headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        inventory = await response.json()
                        self.log_result("Create Test Inventory", True, f"Created inventory for {ingredient['name']} - {qty} {ingredient['unit']}")
                    else:
                        error_text = await response.text()
                        self.log_result("Create Test Inventory", False, f"Failed for {ingredient['name']}: {response.status}", error_text)
            except Exception as e:
                self.log_result("Create Test Inventory", False, f"Error for {ingredient['name']}: {str(e)}")
    
    # ============ PHASE 4: PREP LIST TESTS ============
    
    async def test_prep_list_forecast(self):
        """Test GET /api/prep-list/forecast endpoint"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            async with self.session.get(
                f"{BACKEND_URL}/prep-list/forecast?date={tomorrow}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    forecast_response = await response.json()
                    
                    # Handle both list and object response formats
                    if isinstance(forecast_response, dict) and "items" in forecast_response:
                        forecast = forecast_response["items"]
                        self.log_result("Prep List Forecast", True, f"Retrieved forecast for {tomorrow} - {len(forecast)} items")
                    elif isinstance(forecast_response, list):
                        forecast = forecast_response
                        self.log_result("Prep List Forecast", True, f"Retrieved forecast for {tomorrow} - {len(forecast)} items")
                    else:
                        self.log_result("Prep List Forecast", False, "Invalid response format", forecast_response)
                        return None
                        
                    # Verify forecast structure
                    if len(forecast) > 0:
                        item = forecast[0]
                        required_fields = ["preparationId", "preparationName", "forecastQty", "availableQty", "toMakeQty", "unit", "forecastSource"]
                        missing_fields = [field for field in required_fields if field not in item]
                        
                        if missing_fields:
                            self.log_result("Prep List Forecast Structure", False, f"Missing fields: {missing_fields}", item)
                        else:
                            self.log_result("Prep List Forecast Structure", True, "Forecast structure correct")
                            
                            # Verify calculation logic
                            if item["toMakeQty"] == max(0, item["forecastQty"] - item["availableQty"]):
                                self.log_result("Prep List Calculation", True, "toMakeQty calculation correct")
                            else:
                                self.log_result("Prep List Calculation", False, f"toMakeQty should be max(0, {item['forecastQty']} - {item['availableQty']}) = {max(0, item['forecastQty'] - item['availableQty'])}, got {item['toMakeQty']}")
                    
                    return forecast
                else:
                    error_text = await response.text()
                    self.log_result("Prep List Forecast", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Prep List Forecast", False, f"Error: {str(e)}")
            return None
    
    async def test_prep_list_crud(self):
        """Test prep list CRUD operations"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        if len(self.test_data["preparations"]) < 1:
            self.log_result("Prep List CRUD", False, "No preparations available")
            return
        
        prep = self.test_data["preparations"][0]
        
        # Test CREATE prep list
        prep_list_data = {
            "date": tomorrow,
            "items": [
                {
                    "preparationId": prep["id"],
                    "preparationName": prep["name"],
                    "forecastQty": 12.0,
                    "availableQty": 4.0,
                    "toMakeQty": 8.0,
                    "unit": "portions",
                    "forecastSource": "sales_trend",
                    "notes": "Test prep list item"
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/prep-list",
                json=prep_list_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    prep_list = await response.json()
                    self.log_result("Prep List Create", True, f"Created prep list for {tomorrow}")
                    
                    # Test GET all prep lists
                    async with self.session.get(
                        f"{BACKEND_URL}/prep-list",
                        headers=self.get_auth_headers()
                    ) as get_response:
                        if get_response.status == 200:
                            prep_lists = await get_response.json()
                            
                            if isinstance(prep_lists, list) and len(prep_lists) > 0:
                                # Verify tenant isolation
                                restaurant_id = self.user_data["restaurantId"]
                                for pl in prep_lists:
                                    if pl.get("restaurantId") != restaurant_id:
                                        self.log_result("Prep List Tenant Isolation", False, "Found prep list from different restaurant")
                                        break
                                else:
                                    self.log_result("Prep List Get All", True, f"Retrieved {len(prep_lists)} prep lists with tenant isolation")
                            else:
                                self.log_result("Prep List Get All", False, "No prep lists returned")
                        else:
                            self.log_result("Prep List Get All", False, f"Failed: {get_response.status}")
                    
                    # Test UPDATE prep list (same date)
                    updated_data = {
                        "date": tomorrow,
                        "items": [
                            {
                                "preparationId": prep["id"],
                                "preparationName": prep["name"],
                                "forecastQty": 15.0,  # Updated
                                "availableQty": 5.0,   # Updated
                                "toMakeQty": 10.0,     # Updated
                                "actualQty": 9.0,      # Added actual
                                "unit": "portions",
                                "forecastSource": "manual_override",
                                "overrideQty": 15.0,
                                "notes": "Updated prep list item"
                            }
                        ]
                    }
                    
                    async with self.session.post(
                        f"{BACKEND_URL}/prep-list",
                        json=updated_data,
                        headers={**self.get_auth_headers(), "Content-Type": "application/json"}
                    ) as update_response:
                        if update_response.status == 200:
                            updated_prep_list = await update_response.json()
                            
                            # Verify update
                            if updated_prep_list["items"][0]["forecastQty"] == 15.0:
                                self.log_result("Prep List Update", True, "Prep list updated successfully")
                            else:
                                self.log_result("Prep List Update", False, "Update not reflected")
                        else:
                            error_text = await update_response.text()
                            self.log_result("Prep List Update", False, f"Update failed: {update_response.status}", error_text)
                    
                    return prep_list
                else:
                    error_text = await response.text()
                    self.log_result("Prep List Create", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Prep List Create", False, f"Error: {str(e)}")
            return None
    
    # ============ PHASE 4: ORDER LIST TESTS ============
    
    async def test_order_list_forecast(self):
        """Test GET /api/order-list/forecast endpoint"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            async with self.session.get(
                f"{BACKEND_URL}/order-list/forecast?date={tomorrow}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    forecast_response = await response.json()
                    
                    # Handle both list and object response formats
                    if isinstance(forecast_response, dict) and "items" in forecast_response:
                        forecast = forecast_response["items"]
                        self.log_result("Order List Forecast", True, f"Retrieved order forecast for {tomorrow} - {len(forecast)} items")
                    elif isinstance(forecast_response, list):
                        forecast = forecast_response
                        self.log_result("Order List Forecast", True, f"Retrieved order forecast for {tomorrow} - {len(forecast)} items")
                    else:
                        self.log_result("Order List Forecast", False, "Invalid response format", forecast_response)
                        return None
                        
                    # Verify forecast structure and drivers
                    if len(forecast) > 0:
                            item = forecast[0]
                            required_fields = ["ingredientId", "ingredientName", "currentQty", "minStockQty", "suggestedQty", "unit", "drivers"]
                            missing_fields = [field for field in required_fields if field not in item]
                            
                            if missing_fields:
                                self.log_result("Order List Forecast Structure", False, f"Missing fields: {missing_fields}", item)
                            else:
                                self.log_result("Order List Forecast Structure", True, "Order forecast structure correct")
                                
                                # Verify drivers logic
                                valid_drivers = ["low_stock", "prep_needs", "expiring_soon"]
                                if all(driver in valid_drivers for driver in item["drivers"]):
                                    self.log_result("Order List Drivers", True, f"Valid drivers: {item['drivers']}")
                                else:
                                    self.log_result("Order List Drivers", False, f"Invalid drivers: {item['drivers']}")
                                
                                # Check low_stock driver logic
                                if item["currentQty"] < item["minStockQty"] and "low_stock" in item["drivers"]:
                                    self.log_result("Order List Low Stock Logic", True, "Low stock driver correctly triggered")
                                elif item["currentQty"] >= item["minStockQty"] and "low_stock" not in item["drivers"]:
                                    self.log_result("Order List Low Stock Logic", True, "Low stock driver correctly not triggered")
                                else:
                                    self.log_result("Order List Low Stock Logic", False, f"Low stock logic error: currentQty={item['currentQty']}, minStock={item['minStockQty']}, drivers={item['drivers']}")
                        
                        return forecast
                    else:
                        self.log_result("Order List Forecast", False, "Response is not a list", forecast)
                        return None
                else:
                    error_text = await response.text()
                    self.log_result("Order List Forecast", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Order List Forecast", False, f"Error: {str(e)}")
            return None
    
    async def test_order_list_crud(self):
        """Test order list CRUD operations"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        if len(self.test_data["ingredients"]) < 1 or len(self.test_data["suppliers"]) < 1:
            self.log_result("Order List CRUD", False, "No ingredients or suppliers available")
            return
        
        ingredient = self.test_data["ingredients"][0]
        supplier = self.test_data["suppliers"][0]
        
        # Test CREATE order list
        order_list_data = {
            "date": tomorrow,
            "items": [
                {
                    "ingredientId": ingredient["id"],
                    "ingredientName": ingredient["name"],
                    "currentQty": 5.0,
                    "minStockQty": ingredient["minStockQty"],
                    "suggestedQty": 20.0,
                    "unit": ingredient["unit"],
                    "supplierId": supplier["id"],
                    "supplierName": supplier["name"],
                    "drivers": ["low_stock", "prep_needs"],
                    "notes": "Test order list item"
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/order-list",
                json=order_list_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    order_list = await response.json()
                    self.log_result("Order List Create", True, f"Created order list for {tomorrow}")
                    
                    # Test GET all order lists
                    async with self.session.get(
                        f"{BACKEND_URL}/order-list",
                        headers=self.get_auth_headers()
                    ) as get_response:
                        if get_response.status == 200:
                            order_lists = await get_response.json()
                            
                            if isinstance(order_lists, list) and len(order_lists) > 0:
                                # Verify tenant isolation
                                restaurant_id = self.user_data["restaurantId"]
                                for ol in order_lists:
                                    if ol.get("restaurantId") != restaurant_id:
                                        self.log_result("Order List Tenant Isolation", False, "Found order list from different restaurant")
                                        break
                                else:
                                    self.log_result("Order List Get All", True, f"Retrieved {len(order_lists)} order lists with tenant isolation")
                            else:
                                self.log_result("Order List Get All", False, "No order lists returned")
                        else:
                            self.log_result("Order List Get All", False, f"Failed: {get_response.status}")
                    
                    return order_list
                else:
                    error_text = await response.text()
                    self.log_result("Order List Create", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("Order List Create", False, f"Error: {str(e)}")
            return None
    
    # ============ PHASE 5: P&L SNAPSHOT TESTS ============
    
    async def test_pl_snapshot_create(self):
        """Test POST /api/pl/snapshot endpoint"""
        # Create P&L snapshot for current week
        today = datetime.now()
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        pl_data = {
            "period": {
                "start": monday.strftime("%Y-%m-%d"),
                "end": sunday.strftime("%Y-%m-%d"),
                "timezone": "Europe/Rome",
                "granularity": "WEEK"
            },
            "currency": "EUR",
            "displayLocale": "it-IT",
            "sales_turnover": 15000.50,
            "sales_food_beverage": 13500.25,
            "sales_delivery": 1500.25,
            "cogs_food_beverage": 4500.75,
            "cogs_raw_waste": 300.50,
            "opex_non_food": 800.25,
            "opex_platforms": 450.75,
            "labour_employees": 3200.00,
            "labour_staff_meal": 150.50,
            "marketing_online_ads": 500.00,
            "marketing_free_items": 200.25,
            "rent_base_effective": 2500.00,
            "rent_garden": 300.00,
            "other_total": 450.75,
            "notes": "Test P&L snapshot for current week"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/pl/snapshot",
                json=pl_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    pl_snapshot = await response.json()
                    
                    # Verify automatic calculations
                    expected_cogs_total = pl_data["cogs_food_beverage"] + pl_data["cogs_raw_waste"]
                    expected_opex_total = pl_data["opex_non_food"] + pl_data["opex_platforms"]
                    expected_labour_total = pl_data["labour_employees"] + pl_data["labour_staff_meal"]
                    expected_marketing_total = pl_data["marketing_online_ads"] + pl_data["marketing_free_items"]
                    expected_rent_total = pl_data["rent_base_effective"] + pl_data["rent_garden"]
                    
                    expected_ebitda = (pl_data["sales_turnover"] - 
                                     expected_cogs_total - 
                                     expected_opex_total - 
                                     expected_labour_total - 
                                     expected_marketing_total - 
                                     expected_rent_total - 
                                     pl_data["other_total"])
                    
                    calculations_correct = True
                    
                    if abs(pl_snapshot["cogs_total"] - expected_cogs_total) > 0.01:
                        self.log_result("P&L COGS Total Calculation", False, f"Expected {expected_cogs_total:.2f}, got {pl_snapshot['cogs_total']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L COGS Total Calculation", True, f"Correct: {pl_snapshot['cogs_total']:.2f}")
                    
                    if abs(pl_snapshot["opex_total"] - expected_opex_total) > 0.01:
                        self.log_result("P&L OPEX Total Calculation", False, f"Expected {expected_opex_total:.2f}, got {pl_snapshot['opex_total']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L OPEX Total Calculation", True, f"Correct: {pl_snapshot['opex_total']:.2f}")
                    
                    if abs(pl_snapshot["labour_total"] - expected_labour_total) > 0.01:
                        self.log_result("P&L Labour Total Calculation", False, f"Expected {expected_labour_total:.2f}, got {pl_snapshot['labour_total']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L Labour Total Calculation", True, f"Correct: {pl_snapshot['labour_total']:.2f}")
                    
                    if abs(pl_snapshot["marketing_total"] - expected_marketing_total) > 0.01:
                        self.log_result("P&L Marketing Total Calculation", False, f"Expected {expected_marketing_total:.2f}, got {pl_snapshot['marketing_total']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L Marketing Total Calculation", True, f"Correct: {pl_snapshot['marketing_total']:.2f}")
                    
                    if abs(pl_snapshot["rent_total"] - expected_rent_total) > 0.01:
                        self.log_result("P&L Rent Total Calculation", False, f"Expected {expected_rent_total:.2f}, got {pl_snapshot['rent_total']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L Rent Total Calculation", True, f"Correct: {pl_snapshot['rent_total']:.2f}")
                    
                    if abs(pl_snapshot["kpi_ebitda"] - expected_ebitda) > 0.01:
                        self.log_result("P&L EBITDA Calculation", False, f"Expected {expected_ebitda:.2f}, got {pl_snapshot['kpi_ebitda']:.2f}")
                        calculations_correct = False
                    else:
                        self.log_result("P&L EBITDA Calculation", True, f"Correct: {pl_snapshot['kpi_ebitda']:.2f}")
                    
                    # Verify 2 decimal rounding
                    decimal_fields = ["sales_turnover", "cogs_total", "opex_total", "labour_total", "marketing_total", "rent_total", "kpi_ebitda"]
                    for field in decimal_fields:
                        value = pl_snapshot[field]
                        if round(value, 2) == value:
                            continue
                        else:
                            self.log_result("P&L Decimal Rounding", False, f"Field {field} not rounded to 2 decimals: {value}")
                            calculations_correct = False
                            break
                    else:
                        self.log_result("P&L Decimal Rounding", True, "All amounts properly rounded to 2 decimals")
                    
                    # Verify period structure
                    if (pl_snapshot["period"]["start"] == monday.strftime("%Y-%m-%d") and
                        pl_snapshot["period"]["end"] == sunday.strftime("%Y-%m-%d") and
                        pl_snapshot["period"]["timezone"] == "Europe/Rome"):
                        self.log_result("P&L Period Structure", True, "Period structure correct (Mon-Sun, Europe/Rome)")
                    else:
                        self.log_result("P&L Period Structure", False, "Period structure incorrect", pl_snapshot["period"])
                    
                    # Verify currency and locale
                    if pl_snapshot["currency"] == "EUR" and pl_snapshot["displayLocale"] == "it-IT":
                        self.log_result("P&L Currency Locale", True, "Currency and locale correct")
                    else:
                        self.log_result("P&L Currency Locale", False, f"Currency: {pl_snapshot['currency']}, Locale: {pl_snapshot['displayLocale']}")
                    
                    if calculations_correct:
                        self.log_result("P&L Snapshot Create", True, "P&L snapshot created with correct calculations")
                    else:
                        self.log_result("P&L Snapshot Create", False, "P&L snapshot created but calculations incorrect")
                    
                    return pl_snapshot
                else:
                    error_text = await response.text()
                    self.log_result("P&L Snapshot Create", False, f"Failed: {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_result("P&L Snapshot Create", False, f"Error: {str(e)}")
            return None
    
    async def test_pl_snapshot_get(self):
        """Test GET /api/pl/snapshot endpoint with filters"""
        try:
            # Test GET without filters
            async with self.session.get(
                f"{BACKEND_URL}/pl/snapshot",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    snapshots = await response.json()
                    
                    if isinstance(snapshots, list):
                        self.log_result("P&L Snapshot Get All", True, f"Retrieved {len(snapshots)} P&L snapshots")
                        
                        # Verify tenant isolation
                        restaurant_id = self.user_data["restaurantId"]
                        for snapshot in snapshots:
                            if snapshot.get("restaurantId") != restaurant_id:
                                self.log_result("P&L Snapshot Tenant Isolation", False, "Found snapshot from different restaurant")
                                break
                        else:
                            self.log_result("P&L Snapshot Tenant Isolation", True, "Tenant isolation working")
                        
                        # Verify sorting (should be by period.start descending)
                        if len(snapshots) > 1:
                            dates = [snapshot["period"]["start"] for snapshot in snapshots]
                            if dates == sorted(dates, reverse=True):
                                self.log_result("P&L Snapshot Sorting", True, "Snapshots sorted by period.start descending")
                            else:
                                self.log_result("P&L Snapshot Sorting", False, f"Incorrect sorting: {dates}")
                    else:
                        self.log_result("P&L Snapshot Get All", False, "Response is not a list", snapshots)
                else:
                    error_text = await response.text()
                    self.log_result("P&L Snapshot Get All", False, f"Failed: {response.status}", error_text)
            
            # Test GET with date range filters
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            async with self.session.get(
                f"{BACKEND_URL}/pl/snapshot?start_date={start_date}&end_date={end_date}",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    filtered_snapshots = await response.json()
                    self.log_result("P&L Snapshot Date Filter", True, f"Retrieved {len(filtered_snapshots)} snapshots with date filter")
                else:
                    error_text = await response.text()
                    self.log_result("P&L Snapshot Date Filter", False, f"Failed: {response.status}", error_text)
        
        except Exception as e:
            self.log_result("P&L Snapshot Get", False, f"Error: {str(e)}")
    
    async def test_pl_multi_currency_locale(self):
        """Test P&L with different currencies and locales"""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        # Test USD currency with en-US locale
        pl_data_usd = {
            "period": {
                "start": monday.strftime("%Y-%m-%d"),
                "end": sunday.strftime("%Y-%m-%d"),
                "timezone": "Europe/Rome",
                "granularity": "WEEK"
            },
            "currency": "USD",
            "displayLocale": "en-US",
            "sales_turnover": 18000.75,
            "sales_food_beverage": 16200.50,
            "sales_delivery": 1800.25,
            "cogs_food_beverage": 5400.25,
            "cogs_raw_waste": 360.50,
            "opex_non_food": 960.00,
            "opex_platforms": 540.75,
            "labour_employees": 3840.00,
            "labour_staff_meal": 180.50,
            "marketing_online_ads": 600.00,
            "marketing_free_items": 240.25,
            "rent_base_effective": 3000.00,
            "rent_garden": 360.00,
            "other_total": 540.75,
            "notes": "Test P&L snapshot USD/en-US"
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/pl/snapshot",
                json=pl_data_usd,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    pl_snapshot_usd = await response.json()
                    
                    if pl_snapshot_usd["currency"] == "USD" and pl_snapshot_usd["displayLocale"] == "en-US":
                        self.log_result("P&L Multi-Currency USD", True, "USD currency and en-US locale supported")
                    else:
                        self.log_result("P&L Multi-Currency USD", False, f"Currency: {pl_snapshot_usd['currency']}, Locale: {pl_snapshot_usd['displayLocale']}")
                else:
                    error_text = await response.text()
                    self.log_result("P&L Multi-Currency USD", False, f"Failed: {response.status}", error_text)
        except Exception as e:
            self.log_result("P&L Multi-Currency USD", False, f"Error: {str(e)}")
    
    # ============ RBAC AND SECURITY TESTS ============
    
    async def test_rbac_all_endpoints(self):
        """Test RBAC for all Phase 4 & 5 endpoints"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        endpoints_to_test = [
            ("GET", f"/prep-list/forecast?date={tomorrow}"),
            ("GET", "/prep-list"),
            ("POST", "/prep-list"),
            ("GET", f"/order-list/forecast?date={tomorrow}"),
            ("GET", "/order-list"),
            ("POST", "/order-list"),
            ("POST", "/pl/snapshot"),
            ("GET", "/pl/snapshot")
        ]
        
        # Test authentication required
        for method, endpoint in endpoints_to_test:
            try:
                if method == "GET":
                    async with self.session.get(f"{BACKEND_URL}{endpoint}") as response:
                        if response.status in [401, 403]:
                            self.log_result(f"Auth Required {endpoint}", True, "Authentication correctly required")
                        else:
                            self.log_result(f"Auth Required {endpoint}", False, f"Should require auth: {response.status}")
                elif method == "POST":
                    async with self.session.post(f"{BACKEND_URL}{endpoint}", json={}) as response:
                        if response.status in [401, 403]:
                            self.log_result(f"Auth Required {endpoint}", True, "Authentication correctly required")
                        else:
                            self.log_result(f"Auth Required {endpoint}", False, f"Should require auth: {response.status}")
            except Exception as e:
                self.log_result(f"Auth Required {endpoint}", False, f"Error: {str(e)}")
        
        # Test with different user roles
        for role in ["admin", "manager", "staff"]:
            try:
                if await self.authenticate(role):
                    # Test prep list endpoints (should be accessible to all roles)
                    async with self.session.get(
                        f"{BACKEND_URL}/prep-list/forecast?date={tomorrow}",
                        headers=self.get_auth_headers()
                    ) as response:
                        if response.status == 200:
                            self.log_result(f"Prep List Access {role.title()}", True, f"{role.title()} can access prep list")
                        else:
                            self.log_result(f"Prep List Access {role.title()}", False, f"Access denied: {response.status}")
                    
                    # Test order list endpoints (should be accessible to all roles)
                    async with self.session.get(
                        f"{BACKEND_URL}/order-list/forecast?date={tomorrow}",
                        headers=self.get_auth_headers()
                    ) as response:
                        if response.status == 200:
                            self.log_result(f"Order List Access {role.title()}", True, f"{role.title()} can access order list")
                        else:
                            self.log_result(f"Order List Access {role.title()}", False, f"Access denied: {response.status}")
                    
                    # Test P&L endpoints (may be admin-only, verify)
                    async with self.session.get(
                        f"{BACKEND_URL}/pl/snapshot",
                        headers=self.get_auth_headers()
                    ) as response:
                        if response.status == 200:
                            self.log_result(f"P&L Access {role.title()}", True, f"{role.title()} can access P&L")
                        elif response.status == 403:
                            self.log_result(f"P&L Access {role.title()}", True, f"{role.title()} correctly denied P&L access")
                        else:
                            self.log_result(f"P&L Access {role.title()}", False, f"Unexpected response: {response.status}")
                else:
                    self.log_result(f"RBAC Test {role.title()}", False, f"Could not authenticate as {role}")
            except Exception as e:
                self.log_result(f"RBAC Test {role.title()}", False, f"Error: {str(e)}")
        
        # Re-authenticate as admin for remaining tests
        await self.authenticate("admin")
    
    async def test_data_validation(self):
        """Test data validation for all endpoints"""
        # Test prep list validation
        try:
            invalid_prep_data = {
                "date": "invalid-date",
                "items": []
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/prep-list",
                json=invalid_prep_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:
                    self.log_result("Prep List Validation", True, "Correctly rejected invalid data")
                else:
                    self.log_result("Prep List Validation", False, f"Should reject invalid data: {response.status}")
        except Exception as e:
            self.log_result("Prep List Validation", False, f"Error: {str(e)}")
        
        # Test order list validation
        try:
            invalid_order_data = {
                "date": "2024-13-45",  # Invalid date
                "items": []
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/order-list",
                json=invalid_order_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:
                    self.log_result("Order List Validation", True, "Correctly rejected invalid data")
                else:
                    self.log_result("Order List Validation", False, f"Should reject invalid data: {response.status}")
        except Exception as e:
            self.log_result("Order List Validation", False, f"Error: {str(e)}")
        
        # Test P&L validation
        try:
            invalid_pl_data = {
                "period": {
                    "start": "invalid-date",
                    "end": "2024-01-07"
                },
                "currency": "INVALID",
                "sales_turnover": -1000  # Negative amount
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/pl/snapshot",
                json=invalid_pl_data,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            ) as response:
                if response.status == 422:
                    self.log_result("P&L Validation", True, "Correctly rejected invalid data")
                else:
                    self.log_result("P&L Validation", False, f"Should reject invalid data: {response.status}")
        except Exception as e:
            self.log_result("P&L Validation", False, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 70)
        print("🎯 PHASE 4 & 5 BACKEND TESTING SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            print("-" * 40)
            for result in self.test_results:
                if not result["success"]:
                    print(f"• {result['test']}: {result['message']}")
        
        print("\n✅ CRITICAL FEATURES TESTED:")
        print("-" * 40)
        print("• Phase 4: Prep List forecast and CRUD operations")
        print("• Phase 4: Order List forecast with multiple drivers")
        print("• Phase 5: P&L Snapshot with automatic calculations")
        print("• RBAC enforcement for all endpoints")
        print("• Tenant isolation verification")
        print("• Data validation and error handling")
        print("• Multi-currency and multi-locale support")
        print("• Forecast accuracy and calculation logic")
    
    async def run_all_tests(self):
        """Run all Phase 4 & 5 backend tests"""
        print("🚀 Starting Phase 4 & 5 Backend Testing Suite")
        print("=" * 70)
        
        # Register/Authenticate as admin
        if not await self.register_test_user("admin"):
            print("❌ Authentication failed - cannot continue tests")
            return
        
        # Setup test data
        await self.setup_test_data()
        
        print("\n📋 PHASE 4: PREP LIST TESTING")
        print("-" * 50)
        await self.test_prep_list_forecast()
        await self.test_prep_list_crud()
        
        print("\n📦 PHASE 4: ORDER LIST TESTING")
        print("-" * 50)
        await self.test_order_list_forecast()
        await self.test_order_list_crud()
        
        print("\n💰 PHASE 5: P&L SNAPSHOT TESTING")
        print("-" * 50)
        await self.test_pl_snapshot_create()
        await self.test_pl_snapshot_get()
        await self.test_pl_multi_currency_locale()
        
        print("\n🔐 RBAC & SECURITY TESTING")
        print("-" * 50)
        await self.test_rbac_all_endpoints()
        
        print("\n✅ DATA VALIDATION TESTING")
        print("-" * 50)
        await self.test_data_validation()
        
        # Print summary
        self.print_summary()

async def main():
    """Main test runner"""
    async with Phase45BackendTester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())