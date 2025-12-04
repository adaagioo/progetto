# backend/app/services/email_service.py
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Tuple, Optional

from backend.app.core.config import settings
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_message(to_email: str, subject: str, body: str, html: Optional[str] = None) -> EmailMessage:
	"""
	Build email message with optional HTML content.

	Args:
		to_email: Recipient email address
		subject: Email subject
		body: Plain text body
		html: Optional HTML body

	Returns:
		EmailMessage ready to send
	"""
	msg = EmailMessage()
	msg["From"] = getattr(settings, "MAIL_FROM", None) or "RistoBrain <no-reply@ristobrain.app>"
	msg["To"] = to_email
	msg["Subject"] = subject
	msg.set_content(body)

	# Add HTML alternative if provided
	if html:
		msg.add_alternative(html, subtype="html")

	return msg


def _smtp_client():
	"""
	Create SMTP client connection.

	For MailHog (dev): host=mailhog, port=1025, no auth
	For production: configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

	Returns:
		SMTP client or None if not configured
	"""
	host = getattr(settings, "SMTP_HOST", None)
	if not host:
		logger.warning("SMTP_HOST not configured - email sending disabled")
		return None

	port = int(getattr(settings, "SMTP_PORT", 587) or 587)
	user = getattr(settings, "SMTP_USER", None)
	password = getattr(settings, "SMTP_PASS", None)
	use_starttls = bool(getattr(settings, "SMTP_STARTTLS", True))

	try:
		client = smtplib.SMTP(host, port, timeout=10)

		# MailHog doesn't need STARTTLS, production SMTP usually does
		if use_starttls and port != 1025:  # Skip STARTTLS for MailHog
			client.starttls(context=ssl.create_default_context())

		# Only login if credentials provided (MailHog doesn't need auth)
		if user and password:
			client.login(user, password)

		logger.info(f"SMTP connection established to {host}:{port}")
		return client
	except Exception as e:
		logger.error(f"Failed to connect to SMTP server {host}:{port}: {e}")
		return None


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> bool:
	"""
	Send email via SMTP.

	Args:
		to_email: Recipient email address
		subject: Email subject
		body: Plain text body
		html: Optional HTML body

	Returns:
		True if sent successfully, False otherwise
	"""
	msg = _build_message(to_email, subject, body, html)
	cli = _smtp_client()

	if cli is None:
		logger.error(f"Cannot send email to {to_email}: SMTP not configured")
		return False

	try:
		cli.send_message(msg)
		cli.quit()
		logger.info(f"Email sent successfully to {to_email}: {subject}")
		return True
	except Exception as e:
		logger.error(f"Failed to send email to {to_email}: {e}")
		try:
			cli.quit()
		except Exception:
			pass
		return False


def reset_password_email(to_email: str, token: str, reset_url: Optional[str] = None) -> Tuple[str, str, str]:
	"""
	Generate password reset email content.

	Args:
		to_email: Recipient email
		token: Reset token
		reset_url: Optional URL for password reset (defaults to APP_URL)

	Returns:
		Tuple of (subject, plain_body, html_body)
	"""
	subject = "🔐 Password Reset Request - RistoBrain"

	# Plain text version
	plain_body = (
		f"Hi,\n\n"
		f"We received a request to reset your password for your RistoBrain account.\n\n"
		f"Your reset token (valid for 30 minutes):\n"
		f"{token}\n\n"
		f"If you didn't request this, you can safely ignore this email.\n\n"
		f"Best regards,\n"
		f"The RistoBrain Team"
	)

	# HTML version
	app_url = reset_url or getattr(settings, "APP_URL", "http://localhost:3000")
	html_body = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
	</head>
	<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
		<div style="background-color: #f8f9fa; border-radius: 10px; padding: 30px; margin-bottom: 20px;">
			<h1 style="color: #2c3e50; margin-top: 0;">🔐 Password Reset Request</h1>
			<p style="font-size: 16px;">Hi,</p>
			<p style="font-size: 16px;">We received a request to reset your password for your <strong>RistoBrain</strong> account.</p>

			<div style="background-color: #fff; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; border-radius: 5px;">
				<p style="margin: 0; font-size: 14px; color: #7f8c8d;">Your reset token (valid for 30 minutes):</p>
				<p style="margin: 10px 0 0 0; font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #2c3e50; word-break: break-all;">
					{token}
				</p>
			</div>

			<p style="font-size: 14px; color: #7f8c8d; margin-top: 30px;">
				If you didn't request this, you can safely ignore this email. Your password will remain unchanged.
			</p>
		</div>

		<div style="text-align: center; color: #95a5a6; font-size: 12px;">
			<p>Best regards,<br><strong>The RistoBrain Team</strong></p>
			<p style="margin-top: 20px;">
				<a href="{app_url}" style="color: #3498db; text-decoration: none;">Visit RistoBrain</a>
			</p>
		</div>
	</body>
	</html>
	"""

	return subject, plain_body, html_body


def password_changed_email(to_email: str) -> Tuple[str, str, str]:
	"""
	Generate password changed confirmation email.

	Returns:
		Tuple of (subject, plain_body, html_body)
	"""
	subject = "✅ Password Changed Successfully - RistoBrain"

	plain_body = (
		f"Hi,\n\n"
		f"Your password for RistoBrain was changed successfully.\n\n"
		f"If you didn't make this change, please contact support immediately.\n\n"
		f"Best regards,\n"
		f"The RistoBrain Team"
	)

	app_url = getattr(settings, "APP_URL", "http://localhost:3000")
	html_body = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
	</head>
	<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
		<div style="background-color: #f8f9fa; border-radius: 10px; padding: 30px; margin-bottom: 20px;">
			<h1 style="color: #27ae60; margin-top: 0;">✅ Password Changed Successfully</h1>
			<p style="font-size: 16px;">Hi,</p>
			<p style="font-size: 16px;">Your password for <strong>RistoBrain</strong> was changed successfully.</p>

			<div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0; border-radius: 5px;">
				<p style="margin: 0; color: #155724; font-weight: bold;">✓ Your account is secure</p>
				<p style="margin: 5px 0 0 0; color: #155724; font-size: 14px;">You can now login with your new password.</p>
			</div>

			<div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px;">
				<p style="margin: 0; color: #856404; font-size: 14px;">
					⚠️ If you didn't make this change, please contact support immediately.
				</p>
			</div>
		</div>

		<div style="text-align: center; color: #95a5a6; font-size: 12px;">
			<p>Best regards,<br><strong>The RistoBrain Team</strong></p>
			<p style="margin-top: 20px;">
				<a href="{app_url}" style="color: #3498db; text-decoration: none;">Visit RistoBrain</a>
			</p>
		</div>
	</body>
	</html>
	"""

	return subject, plain_body, html_body
