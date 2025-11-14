# backend/app/utils/text_norm.py
from __future__ import annotations
import re
import unicodedata
from typing import List

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(s: str) -> str:
	if not s:
		return ""
	s = s.strip().lower()
	s = unicodedata.normalize("NFKD", s)
	s = "".join(ch for ch in s if not unicodedata.combining(ch))
	s = _PUNCT_RE.sub(" ", s)
	s = _WS_RE.sub(" ", s).strip()
	return s


def tokenize(s: str) -> List[str]:
	s = normalize_text(s)
	return [t for t in s.split(" ") if t]
