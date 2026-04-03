from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from celery import shared_task

from app.api.schemas import CheckResult, Monitor
from app.core.config import settings
from app.metrics import CHECK_LATENCY, CHECK_REQUESTS
from app.validators.http_validator import HTTPResponseData, JSONSchemaValidator, LatencyValidator, StatusCodeValidator
from app.services.storage import STORE
from alerts import send_webhook_alert


@shared_task(name="watchtower.execute_check")
def execute_check(payload: dict[str, Any]) -> CheckResult:
    monitor = Monitor(**{k: v for k, v in payload.items() if k in Monitor.model_fields})
    run_id = UUID(payload["run_id"])

    timeout = monitor.timeout_seconds or settings.default_request_timeout
    latency_threshold = monitor.latency_ms_threshold or settings.default_latency_ms_threshold

    start = time.perf_counter()
    error_message = None
    status_code: int | None = None
    json_body: dict[str, Any] | None = None

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                monitor.method,
                str(monitor.url),
                headers=monitor.headers,
            )
        status_code = response.status_code
        try:
            json_body = response.json()
        except ValueError:
            json_body = None
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)

    latency_ms = (time.perf_counter() - start) * 1000

    response_data = HTTPResponseData(
        status_code=status_code or 0,
        latency_ms=latency_ms,
        json_body=json_body,
    )

    validators = [
        StatusCodeValidator(monitor.expected_status),
        LatencyValidator(latency_threshold),
    ]
    if monitor.json_schema:
        validators.append(JSONSchemaValidator(monitor.json_schema))

    validation_passed = True
    for validator in validators:
        result = validator.validate(response_data)
        if not result.passed:
            validation_passed = False

    status = "pass" if validation_passed and error_message is None else "fail"

    CHECK_REQUESTS.labels(monitor_id=str(monitor.id), status=status).inc()
    CHECK_LATENCY.labels(monitor_id=str(monitor.id)).observe(latency_ms / 1000)

    result = CheckResult(
        run_id=run_id,
        monitor_id=monitor.id,
        status=status,
        latency_ms=latency_ms,
        status_code=status_code,
        error_message=error_message,
        response_sample=json_body,
    )

    STORE.add_result(result)
    STORE.mark_monitor_run(monitor.id, run_at=datetime.now(UTC))

    if status == "fail" and settings.result_webhook_url:
        send_webhook_alert(settings.result_webhook_url, monitor.id, run_id, error_message)

    return result


@shared_task(name="watchtower.dispatch_scheduled")
def dispatch_scheduled_monitors() -> int:
    now = datetime.now(UTC)
    monitors = STORE.list_scheduled_due(now)
    for monitor in monitors:
        payload = monitor.model_dump()
        payload["run_id"] = str(uuid4())
        payload["reason"] = "scheduled"
        if settings.celery_always_eager:
            execute_check(payload)
        else:
            execute_check.delay(payload)
        STORE.mark_monitor_run(monitor.id, run_at=now)
    return len(monitors)
