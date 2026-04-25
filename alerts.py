from __future__ import annotations

import httpx
from celery import shared_task


@shared_task(
    name="watchtower.dispatch_webhook",
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,       # 1s, 2s, 4s, 8s, 16s …
    retry_backoff_max=300,    # cap at 5 minutes
    max_retries=5,
    acks_late=True,
)
def dispatch_webhook(webhook_url: str, payload: dict) -> None:
    response = httpx.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
