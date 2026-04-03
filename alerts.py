from __future__ import annotations

import httpx


def send_webhook_alert(webhook_url: str, monitor_id, run_id, error_message: str | None) -> None:
    payload = {
        "monitor_id": str(monitor_id),
        "run_id": str(run_id),
        "error": error_message,
    }
    try:
        httpx.post(webhook_url, json=payload, timeout=5)
    except Exception:  # noqa: BLE001
        return
