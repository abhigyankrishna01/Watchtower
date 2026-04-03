from __future__ import annotations

from uuid import UUID, uuid4

from app.api.schemas import CheckResult, Monitor
from app.core.config import settings
from app.executor.worker_client import enqueue_check


def run_monitor(monitor: Monitor, reason: str | None = None) -> CheckResult | None:
    run_id = uuid4()
    result = enqueue_check(monitor, run_id=run_id, reason=reason)
    if settings.celery_always_eager:
        return result
    return None


def schedule_monitor(monitor: Monitor) -> UUID:
    run_id = uuid4()
    enqueue_check(monitor, run_id=run_id, reason="scheduled")
    return run_id
