from __future__ import annotations

from celery import Celery
from celery.schedules import schedule
from celery.signals import celeryd_init
from prometheus_client import start_http_server

from app.core.config import settings

@celeryd_init.connect
def init_worker(**kwargs):
    # Start a Prometheus metrics server on a detached thread on port 8001
    # This allows Prometheus to scrape the worker's metrics directly
    start_http_server(8001)

celery_app = Celery(
    "watchtower",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks"]
)

celery_app.conf.update(
    task_default_queue="default",
    task_routes={
        "watchtower.execute_check": {"queue": "default"},
        "watchtower.dispatch_scheduled": {"queue": "default"}
    },
    worker_concurrency=settings.worker_concurrency,
    beat_schedule={
        "dispatch-scheduled-monitors": {
            "task": "watchtower.dispatch_scheduled",
            "schedule": schedule(settings.scheduler_poll_interval_seconds),
        }
    },
)
