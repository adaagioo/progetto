# backend/app/repositories/login_attempts_repo.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from backend.app.db.mongo import get_db

_COLLECTION = "login_attempts"


async def _col():
	return get_db()[_COLLECTION]


async def _ensure_indexes():
	col = await _col()
	try:
		# Index for efficient rate limit queries
		await col.create_index([("email", 1), ("createdAt", -1)])
	except Exception:
		pass
	try:
		# TTL index to auto-delete old records after 1 hour
		await col.create_index("createdAt", expireAfterSeconds=3600)
	except Exception:
		pass


async def record_login_attempt(email: str, success: bool, ip_address: str = None) -> None:
	"""
	Record a login attempt (successful or failed).
	Old records are automatically deleted after 1 hour via TTL index.
	"""
	await _ensure_indexes()
	col = await _col()
	doc = {
		"email": email.lower(),
		"success": success,
		"ipAddress": ip_address,
		"createdAt": datetime.now(tz=timezone.utc),
	}
	await col.insert_one(doc)


async def check_rate_limit(email: str, max_failed_attempts: int = 5, window_minutes: int = 15) -> bool:
	"""
	Check if email has exceeded rate limit for failed login attempts.
	Returns True if rate limit exceeded (too many failed attempts), False if request is allowed.

	Args:
		email: User email to check
		max_failed_attempts: Maximum failed attempts allowed (default: 5)
		window_minutes: Time window in minutes (default: 15)

	Returns:
		True if rate limit exceeded, False if login attempt is allowed
	"""
	col = await _col()
	now = datetime.now(tz=timezone.utc)
	window_start = now - timedelta(minutes=window_minutes)

	# Count failed login attempts for this email within the time window
	failed_count = await col.count_documents({
		"email": email.lower(),
		"success": False,
		"createdAt": {"$gte": window_start}
	})

	return failed_count >= max_failed_attempts


async def reset_login_attempts(email: str) -> None:
	"""
	Reset (delete) all failed login attempts for an email after successful login.
	"""
	col = await _col()
	await col.delete_many({"email": email.lower(), "success": False})
