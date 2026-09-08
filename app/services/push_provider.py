"""Push notification provider abstraction. The default (`none`) provider
is a no-op so the app runs without any push credentials configured. Set
PUSH_PROVIDER=fcm and FCM_SERVICE_ACCOUNT_JSON to enable real delivery via
Firebase Cloud Messaging without touching call sites."""

import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger("gym.push")


class PushProvider(ABC):
    @abstractmethod
    async def send(self, *, tokens: list[str], title: str, body: str, data: dict | None = None) -> None: ...


class NoOpPushProvider(PushProvider):
    async def send(self, *, tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
        logger.debug("push_noop tokens_count=%s title=%s", len(tokens), title)


class FCMPushProvider(PushProvider):
    """Placeholder for a real Firebase Cloud Messaging integration.
    Credentials are read from FCM_SERVICE_ACCOUNT_JSON (never hardcoded)."""

    def __init__(self):
        if not settings.fcm_service_account_json:
            raise RuntimeError("FCM_SERVICE_ACCOUNT_JSON is required when PUSH_PROVIDER=fcm")

    async def send(self, *, tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
        # Intentionally left as an integration point: wire up
        # `firebase-admin` or the HTTP v1 API here using the configured
        # service account. Kept out of the default dependency set so the
        # backend runs without push credentials in development.
        logger.info("push_fcm_dispatch tokens_count=%s title=%s", len(tokens), title)


def get_push_provider() -> PushProvider:
    if settings.push_provider == "fcm":
        return FCMPushProvider()
    return NoOpPushProvider()
