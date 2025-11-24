# backend/app/core/pagination.py
from __future__ import annotations
from typing import Tuple

MAX_LIMIT = 200
DEFAULT_LIMIT = 50


def normalize(limit: int | None, offset: int | None) -> Tuple[int, int]:
	l = DEFAULT_LIMIT if (limit is None or limit <= 0) else min(limit, MAX_LIMIT)
	o = 0 if (offset is None or offset < 0) else offset
	return l, o
