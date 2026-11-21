from __future__ import annotations

import logging

import httpx
from celery import shared_task

from app.validators.ssrf import SSRFError, safe_request

logger = logging.getLogger(__name__)


@shared_task(
    name="watchtower.dispatch_webhook",
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,       # 1s, 2s, 4s, 8s, 16s …
    retry_backoff_max=300,    # cap at 5 minutes
    max_retries=5,
    acks_late=True,
)
def dispatch_webhook(webhook_url: str, payload: dict) -> None:
    try:
        # Webhook URLs are user-supplied too: same DNS-pinned SSRF protection.
        response = safe_request("POST", webhook_url, json=payload, timeout=10)
    except SSRFError as exc:
        # Not retryable: the target is internal, so retrying cannot help.
        logger.warning("SSRF blocked webhook to %s (%s)", webhook_url, exc)
        return
    response.raise_for_status()
