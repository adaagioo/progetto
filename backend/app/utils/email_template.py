# backend/app/utils/email_templates.py
from __future__ import annotations
from app.core.config import settings


def render_welcome_email(user_email: str) -> tuple[str, str]:
    subject = "Welcome to RistoBrain"
    body = f"Hi {user_email},\n\nVisit {settings.APP_URL} to get started.\n"
    return subject, body
