#!/usr/bin/env python3
"""
Seed super admin for RistoBrain deployment

Creates the default super admin user for initial access:
- email: admin@ristobrain.app
- password: ChangeMe123!
"""

import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ.get('MONGO_URI', os.environ.get('MONGO_URL', 'mongodb://localhost:27017/ristobrain'))
DB_NAME = os.environ.get('MONGO_DB_NAME', os.environ.get('DB_NAME', 'ristobrain'))

# Import hash function after path setup
from backend.app.core.security import hash_password


async def create_super_admin():
    """Create the default super admin user"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    admin_email = "admin@ristobrain.app"
    admin_password = "ChangeMe123!"
    restaurant_id = "default"
    
    print("=" * 60)
    print("RistoBrain Super Admin Setup")
    print("=" * 60)
    
    # Check if admin already exists
    existing = await db.users.find_one({"email": admin_email})
    if existing:
        print(f"✓ Super admin '{admin_email}' already exists")
        client.close()
        return
    
    # Create default restaurant if not exists
    existing_restaurant = await db.restaurants.find_one({"id": restaurant_id})
    if not existing_restaurant:
        restaurant = {
            "id": restaurant_id,
            "name": "RistoBrain Demo",
            "plan": "Pro",
            "subscriptionStatus": "active",
            "currency": {
                "code": "EUR",
                "symbol": "€",
                "decimals": 2
            },
            "defaultLocale": "it-IT",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.restaurants.insert_one(restaurant)
        print(f"✓ Created default restaurant: {restaurant_id}")
    else:
        print(f"✓ Restaurant '{restaurant_id}' already exists")
    
    # Hash password using the app's standard method
    hashed_password = hash_password(admin_password)
    
    # Create super admin user
    admin_user = {
        "email": admin_email,
        "password": hashed_password,
        "displayName": "Super Admin",
        "restaurantId": restaurant_id,
        "roleKey": "owner",
        "locale": "en-US",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(admin_user)
    print(f"✓ Created super admin: {admin_email}")
    
    client.close()
    
    print("\n" + "=" * 60)
    print("Super Admin Created Successfully!")
    print("=" * 60)
    print(f"\nCredentials:")
    print(f"  Email:    {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"\n⚠️  IMPORTANT: Change this password after first login!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(create_super_admin())
