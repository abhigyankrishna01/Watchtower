from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from app.validators.ssrf import is_ssrf_url


class MonitorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    url: str
    method: str = "GET"
    headers: dict[str, str] | None = None
    expected_status: int = 200
    json_schema: dict[str, Any] | None = None
    timeout_seconds: float | None = None
    latency_ms_threshold: int | None = None
    schedule_seconds: int | None = Field(default=None, ge=5)
    webhook_url: str | None = None

    @field_validator("url")
    @classmethod
    def url_must_be_public(cls, v: str) -> str:
        if is_ssrf_url(v):
            raise ValueError(
                "URL targets an internal or private network address and cannot be monitored"
            )
        return v

    @field_validator("webhook_url")
    @classmethod
    def webhook_url_must_be_public(cls, v: str | None) -> str | None:
        if v is not None and is_ssrf_url(v):
            raise ValueError(
                "Webhook URL targets an internal or private network address"
            )
        return v


class Monitor(MonitorCreate):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_state: str = Field(default="UP")
    last_run_at: datetime | None = None
    last_latency_ms: float | None = None
    user_id: str = Field(default="dev_user")


class CheckResult(BaseModel):
    run_id: UUID
    monitor_id: UUID
    status: str
    latency_ms: float
    status_code: int | None = None
    error_message: str | None = None
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    response_sample: dict[str, Any] | None = None


class RunRequest(BaseModel):
    reason: str | None = None


class MonitorList(BaseModel):
    monitors: list[Monitor]


class ResultList(BaseModel):
    results: list[CheckResult]
