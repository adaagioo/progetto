"""
RBAC Permission Enforcement Middleware
Provides decorators and functions to enforce RBAC permissions on API endpoints
"""

from functools import wraps
from fastapi import HTTPException, Depends
from typing import Callable, Optional
from rbac_schema import Resource, Action, DEFAULT_PERMISSIONS, has_permission, merge_permissions


async def get_user_permissions(current_user: dict, db) -> dict:
    """
    Get effective permissions for a user based on their role and restaurant overrides
    
    Args:
        current_user: User dict from get_current_user dependency
        db: Database connection
        
    Returns:
        Dictionary of resource -> actions for the user
    """
    role_key = current_user.get("roleKey", "waiter")
    
    # Get default permissions for role
    default_perms = DEFAULT_PERMISSIONS.get(role_key, {})
    
    # Get restaurant-specific overrides
    restaurant = await db.restaurants.find_one(
        {"id": current_user["restaurantId"]},
        {"_id": 0, "permissionOverrides": 1}
    )
    
    overrides = restaurant.get("permissionOverrides", {}) if restaurant else {}
    role_overrides = overrides.get(role_key, {})
    
    # Merge defaults with overrides
    return merge_permissions(default_perms, role_overrides)


async def check_permission(
    current_user: dict,
    db,
    resource: str,
    action: str,
    raise_exception: bool = True
) -> bool:
    """
    Check if a user has permission to perform an action on a resource
    
    Args:
        current_user: User dict from get_current_user dependency
        db: Database connection
        resource: Resource name (e.g., 'recipes', 'ingredients')
        action: Action name (e.g., 'view', 'create', 'update', 'delete')
        raise_exception: If True, raise HTTPException on denial; if False, return bool
        
    Returns:
        True if permission granted, False otherwise (or raises HTTPException)
    """
    # Get user's effective permissions
    permissions = await get_user_permissions(current_user, db)
    
    # Check if permission exists
    has_perm = has_permission(permissions, resource, action)
    
    if not has_perm and raise_exception:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {action} on {resource}"
        )
    
    return has_perm


def require_permission(resource: str, action: str):
    """
    Decorator to require a specific permission for an endpoint
    
    Usage:
        @app.get("/api/recipes")
        @require_permission(Resource.RECIPES, Action.VIEW)
        async def get_recipes(current_user: dict = Depends(get_current_user)):
            ...
    
    Args:
        resource: Resource name
        action: Action name
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user and db from kwargs
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not db:
                raise HTTPException(status_code=500, detail="Database connection not available")
            
            # Check permission
            await check_permission(current_user, db, resource, action, raise_exception=True)
            
            # Call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def filter_by_view_permission(
    current_user: dict,
    db,
    items: list,
    resource_key_field: str = "resource"
) -> list:
    """
    Filter a list of items based on user's view permission
    Used for navigation menus, resource lists, etc.
    
    Args:
        current_user: User dict
        db: Database connection
        items: List of items with resource field
        resource_key_field: Field name containing resource key
        
    Returns:
        Filtered list of items user can view
    """
    permissions = await get_user_permissions(current_user, db)
    
    filtered = []
    for item in items:
        resource = item.get(resource_key_field)
        if resource and has_permission(permissions, resource, Action.VIEW):
            filtered.append(item)
    
    return filtered


async def get_user_capabilities(current_user: dict, db, resource: str) -> dict:
    """
    Get a user's capabilities for a specific resource
    Useful for frontend to show/hide buttons
    
    Args:
        current_user: User dict
        db: Database connection
        resource: Resource name
        
    Returns:
        Dictionary with canView, canCreate, canUpdate, canDelete booleans
    """
    permissions = await get_user_permissions(current_user, db)
    
    return {
        "canView": has_permission(permissions, resource, Action.VIEW),
        "canCreate": has_permission(permissions, resource, Action.CREATE),
        "canUpdate": has_permission(permissions, resource, Action.UPDATE),
        "canDelete": has_permission(permissions, resource, Action.DELETE),
    }
