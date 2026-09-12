"""Email provider abstraction, mirroring push_provider.py. The default
(`none`) provider just logs, so the app runs without email credentials
configured. Set EMAIL_PROVIDER=brevo and BREVO_API_KEY to enable real
delivery via Brevo's transactional email HTTP API (chosen over SMTP
because Render and similar free-tier hosts commonly block outbound SMTP
ports; an HTTPS API call has no such restriction)."""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger("gym.email")


class EmailProvider(ABC):
    @abstractmethod
    async def send(self, *, to: str, subject: str, text: str) -> None: ...


class NoOpEmailProvider(EmailProvider):
    async def send(self, *, to: str, subject: str, text: str) -> None:
        logger.debug("email_noop to=%s subject=%s", to, subject)


class BrevoEmailProvider(EmailProvider):
    """Sends via Brevo's transactional email API. Free tier: 300
    emails/day, no sending domain required (a single verified sender
    email is enough)."""

    _ENDPOINT = "https://api.brevo.com/v3/smtp/email"

    def __init__(self) -> None:
        if not settings.brevo_api_key:
            raise RuntimeError("BREVO_API_KEY is required when EMAIL_PROVIDER=brevo")

    async def send(self, *, to: str, subject: str, text: str) -> None:
        payload = {
            "sender": {"email": settings.email_from_address, "name": settings.email_from_name},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self._ENDPOINT,
                json=payload,
                headers={"api-key": settings.brevo_api_key, "content-type": "application/json"},
            )
        if response.status_code >= 400:
            logger.error("email_send_failed to=%s status=%s body=%s", to, response.status_code, response.text)
            raise RuntimeError(f"Email provider returned {response.status_code}")
        logger.info("email_sent to=%s subject=%s", to, subject)


def get_email_provider() -> EmailProvider:
    if settings.email_provider == "brevo":
        return BrevoEmailProvider()
    return NoOpEmailProvider()
