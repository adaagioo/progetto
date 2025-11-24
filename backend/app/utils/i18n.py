# backend/app/utils/i18n.py
from __future__ import annotations
from backend.app.core.config import settings


def get_default_locale() -> str:
    return settings.DEFAULT_LOCALE


def is_supported_locale(locale: str) -> bool:
    return locale in settings.SUPPORTED_LOCALES
