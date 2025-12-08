"""
RBAC Permission Schema
Defines default roles, resources, and actions for the RBAC system
"""

from typing import Dict, List, Any
from enum import Enum


class Action(str, Enum):
    """Standard CRUD actions"""
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Resource(str, Enum):
    """System resources that can be protected"""
    DASHBOARD = "dashboard"
    RECIPES = "recipes"
    INGREDIENTS = "ingredients"
    PREPARATIONS = "preparations"
    SUPPLIERS = "suppliers"
    RECEIVING = "receiving"
    INVENTORY = "inventory"
    SALES = "sales"
    WASTAGE = "wastage"
    PREP_LIST = "prep_list"
    ORDER_LIST = "order_list"
    PL_SNAPSHOT = "pl_snapshot"
    USERS = "users"
    SETTINGS = "settings"
    RBAC = "rbac"


# Default permission matrix for each role
DEFAULT_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    "owner": {
        # Owner has full access to everything (same as admin)
        Resource.DASHBOARD: [Action.VIEW],
        Resource.RECIPES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INGREDIENTS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREPARATIONS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SUPPLIERS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.RECEIVING: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INVENTORY: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SALES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.WASTAGE: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREP_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.ORDER_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PL_SNAPSHOT: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.USERS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SETTINGS: [Action.VIEW, Action.UPDATE],
        Resource.RBAC: [Action.VIEW, Action.UPDATE],
    },
    "admin": {
        # Admin has full access to everything
        Resource.DASHBOARD: [Action.VIEW],
        Resource.RECIPES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INGREDIENTS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREPARATIONS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SUPPLIERS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.RECEIVING: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INVENTORY: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SALES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.WASTAGE: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREP_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.ORDER_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PL_SNAPSHOT: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.USERS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SETTINGS: [Action.VIEW, Action.UPDATE],
        Resource.RBAC: [Action.VIEW, Action.UPDATE],
    },
    "manager": {
        # Manager has most access except user management and RBAC
        Resource.DASHBOARD: [Action.VIEW],
        Resource.RECIPES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INGREDIENTS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREPARATIONS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SUPPLIERS: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.RECEIVING: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.INVENTORY: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.SALES: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.WASTAGE: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PREP_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.ORDER_LIST: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.PL_SNAPSHOT: [Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE],
        Resource.USERS: [],  # No user management
        Resource.SETTINGS: [Action.VIEW, Action.UPDATE],
        Resource.RBAC: [],  # No RBAC access
    },
    "waiter": {
        # Waiter (staff) has read-only access to most resources
        Resource.DASHBOARD: [Action.VIEW],
        Resource.RECIPES: [Action.VIEW],
        Resource.INGREDIENTS: [Action.VIEW],
        Resource.PREPARATIONS: [Action.VIEW],
        Resource.SUPPLIERS: [Action.VIEW],
        Resource.RECEIVING: [Action.VIEW],
        Resource.INVENTORY: [Action.VIEW],
        Resource.SALES: [Action.VIEW, Action.CREATE],  # Can create sales
        Resource.WASTAGE: [Action.VIEW, Action.CREATE],  # Can report wastage
        Resource.PREP_LIST: [Action.VIEW],
        Resource.ORDER_LIST: [Action.VIEW],
        Resource.PL_SNAPSHOT: [Action.VIEW],
        Resource.USERS: [],  # No access
        Resource.SETTINGS: [Action.VIEW],
        Resource.RBAC: [],  # No RBAC access
    },
}


def get_default_permissions(role_key: str) -> Dict[str, List[str]]:
    return DEFAULT_PERMISSIONS.get(role_key, {})


def has_permission(
    permissions: Dict[str, List[str]],
    resource: str,
    action: str
) -> bool:
    resource_actions = permissions.get(resource, [])
    return action in resource_actions


def merge_permissions(
    default: Dict[str, List[str]],
    overrides: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    merged = default.copy()
    for resource, actions in overrides.items():
        merged[resource] = actions
    return merged
