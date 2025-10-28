# backend/app/utils/file_utils.py
from __future__ import annotations


def safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", ".", "_", "-")).strip()
