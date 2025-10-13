"""
RBAC (Role-Based Access Control) utilities
"""

# Default permission keys
DEFAULT_PERMISSIONS = {
    "admin": [
        "ingredients.read", "ingredients.write", "ingredients.delete",
        "recipes.read", "recipes.write", "recipes.delete",
        "inventory.read", "inventory.write", "inventory.delete",
        "sales.read", "sales.write", "sales.delete", "sales.import",
        "wastage.read", "wastage.write", "wastage.delete",
        "pl.read", "pl.write", "pl.delete",
        "dashboard.read",
        "settings.write", "settings.roles", "settings.currency"
    ],
    "manager": [
        "ingredients.read", "ingredients.write",
        "recipes.read", "recipes.write",
        "inventory.read", "inventory.write",
        "sales.read", "sales.write", "sales.import",
        "wastage.read", "wastage.write",
        "pl.read",
        "dashboard.read"
    ],
    "waiter": [
        "recipes.read",
        "inventory.read", "inventory.write",
        "sales.read", "sales.write",
        "dashboard.read"
    ]
}

async def get_user_permissions(db, user: dict) -> list:
    """Get user's permissions based on their role"""
    role_key = user.get("roleKey", "waiter")
    
    # Check if custom role exists for this restaurant
    custom_role = await db.roles.find_one({
        "restaurantId": user["restaurantId"],
        "key": role_key
    })
    
    if custom_role:
        return custom_role.get("permissions", [])
    
    # Return default permissions
    return DEFAULT_PERMISSIONS.get(role_key, DEFAULT_PERMISSIONS["waiter"])

def has_permission(user_permissions: list, required_permission: str) -> bool:
    """Check if user has a specific permission"""
    return required_permission in user_permissions

async def seed_default_roles(db, restaurant_id: str):
    """Seed default roles for a new restaurant"""
    default_roles = [
        {
            "restaurantId": restaurant_id,
            "name": "Administrator",
            "key": "admin",
            "permissions": DEFAULT_PERMISSIONS["admin"],
            "isDefault": True
        },
        {
            "restaurantId": restaurant_id,
            "name": "Manager",
            "key": "manager",
            "permissions": DEFAULT_PERMISSIONS["manager"],
            "isDefault": True
        },
        {
            "restaurantId": restaurant_id,
            "name": "Waiter",
            "key": "waiter",
            "permissions": DEFAULT_PERMISSIONS["waiter"],
            "isDefault": True
        }
    ]
    
    await db.roles.insert_many(default_roles)
