import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)


def dispatch_alert_webhook(alert: dict[str, Any]) -> None:
    urls = [
        value
        for value in (
            os.getenv("DISCORD_WEBHOOK_URL"),
            os.getenv("TELEGRAM_WEBHOOK_URL"),
            os.getenv("ALERTS_WEBHOOK_URL"),
        )
        if value
    ]
    for url in urls:
        try:
            httpx.post(url, json=alert, timeout=10.0)
        except httpx.HTTPError:
            logger.exception("alert_webhook_dispatch_failed")
