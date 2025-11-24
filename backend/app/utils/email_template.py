# backend/app/utils/email_templates.py
from __future__ import annotations
from backend.app.core.config import settings


def render_welcome_email(user_email: str) -> tuple[str, str]:
	subject = "Welcome to RistoBrain"
	body = f"Hi {user_email},\n\nVisit {settings.APP_URL} to get started.\n"
	return subject, body


# def get_reset_email_template(locale: str, reset_url: str, user_name: str) -> dict:
# 	templates = {
# 		"en": {
# 			"subject": "RistoBrain - Password Reset Request",
# 			"body": f"""
# 			Hello {user_name},
# 			We received a request to reset your password for your RistoBrain account.
# 			Click the link below to reset your password:
# 			{reset_url}
#
# 			This link will expire in 30 minutes and can only be used once.
# 			If you didn't request this password reset, please ignore this email.
#
# 			Best regards,
# 			The RistoBrain Team
# 			"""
# 		},
# 		"it": {
# 			"subject": "RistoBrain - Richiesta di Reimpostazione Password",
# 			"body": f"""
# 			Ciao {user_name},
# 			Abbiamo ricevuto una richiesta per reimpostare la password del tuo account RistoBrain
# 			Clicca sul link qui sotto per reimpostare la password:
# 			{reset_url}
#
# 			Questo link scadrà tra 30 minuti e può essere utilizzato una sola volta.
# 			Se non hai richiesto questa reimpostazione, ignora questa email.
#
# 			Cordiali saluti,
# 			Il Team di RistoBrain
# 			"""
# 		}
# 	}
#
# 	return templates.get(locale, templates["en"])
#
#
# def get_password_changed_email_template(locale: str, user_name: str) -> dict:
# 	templates = {
# 		"en": {
# 			"subject": "RistoBrain - Password Changed Successfully",
# 			"body": f"""
# 			Hello {user_name},
# 			Your RistoBrain password has been changed successfully.
# 			If you didn't make this change, please contact support immediately.
#
# 			Best regards,
# 			The RistoBrain Team
# 			"""
# 		},
# 		"it": {
# 			"subject": "RistoBrain - Password Modificata con Successo",
# 			"body": f"""
# 			Ciao {user_name},
# 			La tua password di RistoBrain è stata modificata con successo.
# 			Se non hai effettuato questa modifica, contatta immediatamente il supporto.
#
# 			Cordiali saluti,
# 			Il Team di RistoBrain
# 			"""
# 		}
# 	}
#
# 	return templates.get(locale, templates["en"])
