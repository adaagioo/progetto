# backend/app/schemas/rbac.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Dict, List


class RolePermissions(BaseModel):
	roleKey: str
	permissions: Dict[str, List[str]]
