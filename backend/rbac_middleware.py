"""
[LEGACY SHIM] RBAC helpers moved under app.core.rbac_utils.
This module re-exports the new functions to keep imports working.
"""
from app.core.rbac_utils import get_user_permissions, get_resource_access  # noqa: F401
