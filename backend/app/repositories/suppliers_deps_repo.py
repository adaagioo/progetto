# backend/app/repositories/suppliers_deps_repo.py
from __future__ import annotations
from typing import Tuple
from bson import ObjectId
from backend.app.db.mongo import get_db


def _inventory(): return get_db()["inventory"]


def _movements(): return get_db()["inventory_movements"]


async def count_inventory_defaults(supplier_id: str) -> int:
	sid = ObjectId(supplier_id)
	q = {"$or": [
		{"defaultSupplierId": supplier_id},
		{"defaultSupplierId": sid}
	]}
	return await _inventory().count_documents(q)


async def count_receiving_links(supplier_id: str) -> int:
	sid = ObjectId(supplier_id)
	q = {"kind": "receiving", "supplierId": sid}
	return await _movements().count_documents(q)


async def summarize_supplier_dependencies(supplier_id: str) -> Tuple[int, int]:
	inv_defaults = await count_inventory_defaults(supplier_id)
	recv_refs = await count_receiving_links(supplier_id)
	return inv_defaults, recv_refs
