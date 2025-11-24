# backend/app/api/V1/health.py
from __future__ import annotations

from fastapi import APIRouter
from backend.app.db.mongo import get_db

router = APIRouter()


@router.get("/health/live")
async def live():
	"""Liveness probe: process is up."""
	return {"ok": True}


@router.get("/health/ready")
async def ready():
	"""Readiness probe: checks database connectivity."""
	try:
		db = get_db()
		# A lightweight ping. With Motor, you can call command on the database.
		await db.command("ping")
		return {"ok": True, "db": "ok"}
	except Exception as e:
		# Do not leak internals; keep it simple for probes.
		return {"ok": False, "db": "error"}
