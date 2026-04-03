from __future__ import annotations

from app.api.schemas import Monitor
from app.scheduler.scheduler import run_monitor


def run_once(monitor: Monitor) -> None:
    run_monitor(monitor, reason="manual")
