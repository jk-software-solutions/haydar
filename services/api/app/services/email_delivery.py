import asyncio
import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _send_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        if settings.smtp_use_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


async def send_password_reset_email(*, recipient: str, token: str) -> bool:
    """Deliver a password reset token without exposing it through the API response.

    Returning ``False`` means the client-owned SMTP integration is not configured. The
    caller intentionally keeps the public response generic to prevent account discovery.
    """

    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("password_reset_delivery_not_configured")
        return False
    separator = "&" if "?" in settings.password_reset_url_base else "?"
    reset_url = f"{settings.password_reset_url_base}{separator}{urlencode({'token': token})}"
    message = EmailMessage()
    message["Subject"] = "HADIR password reset"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your HADIR account.\n\n"
        f"Reset your password: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_token_minutes} minutes. "
        "If you did not request it, ignore this message."
    )
    try:
        await asyncio.to_thread(_send_smtp, message)
    except (OSError, smtplib.SMTPException):
        logger.exception("password_reset_delivery_failed")
        return False
    return True
