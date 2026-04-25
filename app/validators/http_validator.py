from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

from app.validators.base import ValidationResult, Validator


@dataclass
class HTTPResponseData:
    status_code: int
    latency_ms: float
    json_body: dict[str, Any] | None


class StatusCodeValidator(Validator):
    name = "status_code"

    def __init__(self, expected_status: int) -> None:
        self.expected_status = expected_status

    def validate(self, response: HTTPResponseData) -> ValidationResult:
        passed = response.status_code == self.expected_status
        return ValidationResult(
            passed=passed,
            rule=self.name,
            message=None if passed else f"Expected status {self.expected_status} but got {response.status_code}",
        )


class JSONSchemaValidator(Validator):
    name = "json_schema"

    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema

    def validate(self, response: HTTPResponseData) -> ValidationResult:
        if response.json_body is None:
            return ValidationResult(False, self.name, message="Response body is not JSON")
        try:
            validate(instance=response.json_body, schema=self.schema)
        except ValidationError as exc:
            return ValidationResult(False, self.name, message=str(exc))
        return ValidationResult(True, self.name)


class LatencyValidator(Validator):
    name = "latency"

    def __init__(self, max_latency_ms: int) -> None:
        self.max_latency_ms = max_latency_ms

    def validate(self, response: HTTPResponseData) -> ValidationResult:
        passed = response.latency_ms <= self.max_latency_ms
        return ValidationResult(
            passed=passed,
            rule=self.name,
            message=None if passed else f"Latency {response.latency_ms:.2f} ms exceeded {self.max_latency_ms} ms",
        )
