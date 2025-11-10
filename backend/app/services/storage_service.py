# backend/app/services/storage_service.py
from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
from backend.app.core.config import settings


class LocalStorage:
	def __init__(self, root: Optional[str] = None):
		root_path = root or getattr(settings, "STORAGE_LOCAL_PATH", "/tmp/storage")
		self.root = Path(root_path)
		self.root.mkdir(parents=True, exist_ok=True)

	def save_file(self, filename: str, content_type: Optional[str], data: bytes) -> Tuple[str, int]:
		# Returns (path, size)
		safe_name = filename.replace("/", "_")
		path = self.root / safe_name
		with open(path, "wb") as f:
			f.write(data)
		size = path.stat().st_size
		return str(path), size

	def open_file(self, path: str) -> bytes:
		with open(path, "rb") as f:
			return f.read()

	def delete_file(self, path: str) -> bool:
		p = Path(path)
		if p.exists():
			p.unlink()
			return True
		return False

	def get_public_url(self, path: str) -> str:
		# For local dev we just return the filesystem path.
		return path


_storage: Optional[LocalStorage] = None


def get_storage() -> LocalStorage:
	global _storage
	if _storage is None:
		_storage = LocalStorage()
	return _storage
