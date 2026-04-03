from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class MonitorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    url: HttpUrl
    method: str = "GET"
    headers: dict[str, str] | None = None
    expected_status: int = 200
    json_schema: dict[str, Any] | None = None
    timeout_seconds: float | None = None
    latency_ms_threshold: int | None = None
    schedule_seconds: int | None = Field(default=None, ge=5)


class Monitor(MonitorCreate):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CheckResult(BaseModel):
    run_id: UUID
    monitor_id: UUID
    status: str
    latency_ms: float
    status_code: int | None = None
    error_message: str | None = None
    validated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response_sample: dict[str, Any] | None = None


class RunRequest(BaseModel):
    reason: str | None = None


class MonitorList(BaseModel):
    monitors: list[Monitor]


class ResultList(BaseModel):
    results: list[CheckResult]
