#!/usr/bin/env python3
"""
Seed test data for RistoBrain

Creates test restaurant with admin, manager, and waiter users
"""

import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import bcrypt
from datetime import datetime, timezone
import uuid

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ.get('MONGO_URI', os.environ.get('MONGO_URL', 'mongodb://localhost:27017/ristobrain'))
DB_NAME = os.environ.get('MONGO_DB_NAME', os.environ.get('DB_NAME', 'ristobrain'))
DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'EUR')
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'it-IT')


async def seed_default_roles(db, restaurant_id: str):
    """Seed default RBAC roles for a restaurant"""
    default_roles = [
        {"roleKey": "admin", "restaurantId": restaurant_id, "permissions": {}},
        {"roleKey": "manager", "restaurantId": restaurant_id, "permissions": {}},
        {"roleKey": "waiter", "restaurantId": restaurant_id, "permissions": {}},
    ]
    for role in default_roles:
        await db.rbac_roles.update_one(
            {"roleKey": role["roleKey"]},
            {"$setOnInsert": role},
            upsert=True
        )
DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'EUR')
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'it-IT')

async def seed_data():
    """Seed test data"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("="*60)
    print("Seeding Test Data for RistoBrain")
    print("="*60)
    
    # Create test restaurant
    restaurant_id = "ristorante1"
    
    # Check if restaurant already exists
    existing = await db.restaurants.find_one({"id": restaurant_id})
    if existing:
        print(f"✓ Restaurant '{restaurant_id}' already exists")
    else:
        restaurant = {
            "id": restaurant_id,
            "name": "Ristorante Test",
            "plan": "Pro",
            "subscriptionStatus": "active",
            "ownerUserId": "admin1",
            "currency": {
                "code": DEFAULT_CURRENCY,
                "symbol": "€" if DEFAULT_CURRENCY == "EUR" else "$",
                "decimals": 2
            },
            "defaultLocale": DEFAULT_LOCALE,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.restaurants.insert_one(restaurant)
        print(f"✓ Created restaurant: {restaurant_id}")
        
        # Seed roles
        await seed_default_roles(db, restaurant_id)
        print(f"✓ Seeded default roles")
    
    # Create test users
    test_users = [
        {
            "id": "admin1",
            "email": "admin@test.com",
            "password": "admin123",
            "displayName": "Admin User",
            "role": "admin",
            "roleKey": "admin",
            "locale": "it-IT"
        },
        {
            "id": "manager1",
            "email": "manager@test.com",
            "password": "manager123",
            "displayName": "Manager User",
            "role": "manager",
            "roleKey": "manager",
            "locale": "it-IT"
        },
        {
            "id": "staff1",
            "email": "staff@test.com",
            "password": "staff123",
            "displayName": "Staff User",
            "role": "waiter",
            "roleKey": "waiter",
            "locale": "en-US"
        }
    ]
    
    for user_data in test_users:
        existing_user = await db.users.find_one({"email": user_data["email"]})
        if existing_user:
            print(f"✓ User {user_data['email']} already exists")
        else:
            # Hash password
            hashed_password = bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt())
            
            user = {
                "id": user_data["id"],
                "email": user_data["email"],
                "password": hashed_password.decode('utf-8'),
                "displayName": user_data["displayName"],
                "restaurantId": restaurant_id,
                "role": user_data["role"],
                "roleKey": user_data["roleKey"],
                "locale": user_data["locale"],
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
            print(f"✓ Created user: {user_data['email']} (password: {user_data['password']})")
    
    client.close()
    
    print("\n" + "="*60)
    print("Test Data Seeded Successfully!")
    print("="*60)
    print("\nTest Users:")
    print("  Admin:   admin@test.com / admin123")
    print("  Manager: manager@test.com / manager123")
    print("  Staff:   staff@test.com / staff123")
    print("\nRestaurant ID: ristorante1")
    print(f"Currency: {DEFAULT_CURRENCY}")
    print(f"Locale: {DEFAULT_LOCALE}")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(seed_data())
