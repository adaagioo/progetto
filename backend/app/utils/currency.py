# backend/app/utils/currency.py
from __future__ import annotations
from backend.app.core.config import settings


def normalize_minor_units(amount: float, currency: str | None = None) -> int:
    # Placeholder: gestisci numero di decimali per valuta (es. JPY=0, EUR=2)
    cur = (currency or settings.DEFAULT_CURRENCY).upper()
    decimals = 0 if cur in {"JPY"} else 2
    return int(round(amount * (10 ** decimals), 0))
