"""
i18n messages for API responses and validation
"""

MESSAGES = {
    "en": {
        # Auth
        "auth.login_success": "Login successful",
        "auth.register_success": "Account created successfully",
        "auth.invalid_credentials": "Invalid email or password",
        "auth.email_exists": "Email already registered",
        "auth.token_expired": "Session expired. Please login again",
        "auth.unauthorized": "Unauthorized access",
        
        # Password Reset
        "auth.reset_email_sent": "Password reset email sent. Check your inbox",
        "auth.reset_success": "Password reset successful",
        "auth.reset_token_invalid": "Invalid or expired reset token",
        "auth.reset_token_consumed": "Reset token already used",
        "auth.reset_rate_limit": "Too many requests. Please try again later",
        
        # CRUD
        "crud.created": "{entity} created successfully",
        "crud.updated": "{entity} updated successfully",
        "crud.deleted": "{entity} deleted successfully",
        "crud.not_found": "{entity} not found",
        
        # Permissions
        "permission.denied": "You don't have permission to perform this action",
        "permission.admin_required": "Admin access required",
        
        # Subscription
        "subscription.suspended": "Subscription suspended. Please update payment",
        "subscription.inactive": "Subscription inactive",
        
        # Validation
        "validation.required": "{field} is required",
        "validation.invalid_format": "Invalid {field} format",
        "validation.min_length": "{field} must be at least {min} characters",
        "validation.amount_invalid": "Invalid amount format"
    },
    "it": {
        # Auth
        "auth.login_success": "Accesso effettuato con successo",
        "auth.register_success": "Account creato con successo",
        "auth.invalid_credentials": "Email o password non validi",
        "auth.email_exists": "Email già registrata",
        "auth.token_expired": "Sessione scaduta. Effettua nuovamente l'accesso",
        "auth.unauthorized": "Accesso non autorizzato",
        
        # Password Reset
        "auth.reset_email_sent": "Email di reimpostazione password inviata. Controlla la tua casella di posta",
        "auth.reset_success": "Password reimpostata con successo",
        "auth.reset_token_invalid": "Token di reimpostazione non valido o scaduto",
        "auth.reset_token_consumed": "Token di reimpostazione già utilizzato",
        "auth.reset_rate_limit": "Troppe richieste. Riprova più tardi",
        
        # CRUD
        "crud.created": "{entity} creato con successo",
        "crud.updated": "{entity} aggiornato con successo",
        "crud.deleted": "{entity} eliminato con successo",
        "crud.not_found": "{entity} non trovato",
        
        # Permissions
        "permission.denied": "Non hai il permesso di eseguire questa azione",
        "permission.admin_required": "Accesso amministratore richiesto",
        
        # Subscription
        "subscription.suspended": "Abbonamento sospeso. Aggiorna il pagamento",
        "subscription.inactive": "Abbonamento inattivo",
        
        # Validation
        "validation.required": "{field} è obbligatorio",
        "validation.invalid_format": "Formato {field} non valido",
        "validation.min_length": "{field} deve contenere almeno {min} caratteri",
        "validation.amount_invalid": "Formato importo non valido"
    }
}

def get_message(key: str, locale: str = "en", **kwargs) -> str:
    """Get localized message
    
    Args:
        key: Message key (e.g., "auth.login_success")
        locale: Locale code (e.g., "en", "it", "en-US", "it-IT")
        **kwargs: Format parameters
    
    Returns:
        Localized message string
    """
    # Extract language code from locale
    lang = locale.split("-")[0] if "-" in locale else locale
    
    # Get messages for language, fallback to English
    messages = MESSAGES.get(lang, MESSAGES["en"])
    
    # Get message, fallback to key
    message = messages.get(key, MESSAGES["en"].get(key, key))
    
    # Format with kwargs if provided
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass
    
    return message
