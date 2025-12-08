# backend/app/services/storage_service.py
from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
from backend.app.core.config import settings


class LocalStorage:
	def __init__(self, root: Optional[str] = None):
		root_path = root or getattr(settings, "STORAGE_LOCAL_PATH", "/tmp/storage")
		self.root = Path(root_path).resolve()  # Canonicalize root path
		self.root.mkdir(parents=True, exist_ok=True)

	def _sanitize_filename(self, filename: str) -> str:
		"""Sanitize filename to prevent path traversal attacks."""
		# Remove any path separators and parent directory references
		safe_name = Path(filename).name  # Gets only the filename, strips any path
		# Remove any remaining dangerous characters
		safe_name = safe_name.replace("..", "").replace("/", "_").replace("\\", "_")
		if not safe_name or safe_name in (".", ".."):
			raise ValueError(f"Invalid filename: {filename}")
		return safe_name

	def _validate_path(self, path: str) -> Path:
		"""Validate that path is within storage root to prevent path traversal."""
		abs_path = Path(path).resolve()
		try:
			# Check if path is relative to root
			abs_path.relative_to(self.root)
			return abs_path
		except ValueError:
			raise ValueError(f"Path traversal attempt detected: {path}")

	def save_file(self, filename: str, content_type: Optional[str], data: bytes) -> Tuple[str, int]:
		# Returns (path, size)
		safe_name = self._sanitize_filename(filename)
		path = self.root / safe_name
		# Double-check the final path is safe
		validated_path = self._validate_path(str(path))
		with open(validated_path, "wb") as f:
			f.write(data)
		size = validated_path.stat().st_size
		return str(validated_path), size

	def open_file(self, path: str) -> bytes:
		validated_path = self._validate_path(path)
		with open(validated_path, "rb") as f:
			return f.read()

	def delete_file(self, path: str) -> bool:
		validated_path = self._validate_path(path)
		if validated_path.exists():
			validated_path.unlink()
			return True
		return False

	def get_public_url(self, path: str) -> str:
		# For local dev we just return the filesystem path.
		# Validate the path first
		validated_path = self._validate_path(path)
		return str(validated_path)

	def read_file(self, path: str) -> bytes:
		validated_path = self._validate_path(path)
		return validated_path.read_bytes()


_storage: Optional[LocalStorage] = None


def get_storage() -> LocalStorage:
	global _storage
	if _storage is None:
		_storage = LocalStorage()
	return _storage
