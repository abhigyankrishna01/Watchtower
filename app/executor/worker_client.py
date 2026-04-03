from __future__ import annotations

from uuid import UUID

from app.api.schemas import CheckResult, Monitor
from app.core.config import settings
from worker.celery_app import celery_app


def enqueue_check(monitor: Monitor, run_id: UUID, reason: str | None = None) -> CheckResult | None:
    payload = monitor.model_dump()
    payload["run_id"] = str(run_id)
    payload["reason"] = reason

    if settings.celery_always_eager:
        from worker.tasks import execute_check

        return execute_check(payload)

    celery_app.send_task("watchtower.execute_check", args=[payload])
    return None
