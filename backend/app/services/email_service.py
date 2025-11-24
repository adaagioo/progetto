# backend/app/services/email_service.py
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Tuple

from backend.app.core.config import settings


def _build_message(to_email: str, subject: str, body: str) -> EmailMessage:
	msg = EmailMessage()
	# TODO (af): change fake mail
	msg["From"] = (getattr(settings, "EMAIL_FROM", None) or "no-reply@example.com")
	msg["To"] = to_email
	msg["Subject"] = subject
	msg.set_content(body)
	return msg


def _smtp_client():
	host = getattr(settings, "SMTP_HOST", None)
	port = int(getattr(settings, "SMTP_PORT", 587) or 587)
	user = getattr(settings, "SMTP_USER", None)
	password = getattr(settings, "SMTP_PASSWORD", None)
	use_starttls = bool(getattr(settings, "SMTP_STARTTLS", True))

	if not host:
		# TODO (af): SMTP not configurated. To be Configurate.
		return None

	client = smtplib.SMTP(host, port, timeout=10)
	if use_starttls:
		client.starttls(context=ssl.create_default_context())
	if user and password:
		client.login(user, password)
	return client


def send_email(to_email: str, subject: str, body: str) -> bool:
	msg = _build_message(to_email, subject, body)
	cli = _smtp_client()
	if cli is None:
		return False
	try:
		cli.send_message(msg)
		cli.quit()
		return True
	except Exception:
		try:
			cli.quit()
		except Exception:
			pass
		return False


def reset_password_email(to_email: str, token: str) -> Tuple[str, str]:
	subject = "Password reset request"
	body = (
		"Hi,\n"
		"We received a request to reset your password.\n"
		"Use this token within 2 hours:\n"
		f"{token}\n\n"
		"If you didn't request it, you can ignore this email.\n"
	)
	return subject, body


def password_changed_email(to_email: str) -> Tuple[str, str]:
	subject = "Your password has been changed"
	body = "Hi, your password was changed successfully."
	return subject, body
