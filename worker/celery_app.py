from __future__ import annotations

from celery import Celery
from celery.schedules import schedule

from app.core.config import settings

celery_app = Celery(
    "watchtower",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_routes={"watchtower.execute_check": {"queue": "default"}},
    task_track_started=True,
    worker_concurrency=settings.worker_concurrency,
    beat_schedule={
        "dispatch-scheduled-monitors": {
            "task": "watchtower.dispatch_scheduled",
            "schedule": schedule(settings.scheduler_poll_interval_seconds),
        }
    },
)
