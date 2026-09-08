"""Periodic membership-expiry sweep. Run in-process via the app lifespan by
default (fine for a single/small deployment); for a multi-instance
deployment, disable this and instead invoke
`app.services.membership_service.expire_stale_subscriptions` from an
external scheduler (cron, Celery beat, k8s CronJob) so it only runs once
regardless of replica count."""

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.membership_service import expire_stale_subscriptions

logger = logging.getLogger("gym.tasks")

_INTERVAL_SECONDS = 3600


async def run_forever() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                count = await expire_stale_subscriptions(session)
                if count:
                    logger.info("membership_expiry_swept count=%s", count)
        except Exception:
            logger.exception("membership_expiry_sweep_failed")
        await asyncio.sleep(_INTERVAL_SECONDS)
