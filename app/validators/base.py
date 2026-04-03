from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    rule: str
    message: str | None = None
    details: dict[str, Any] | None = None


class Validator(ABC):
    name: str = "validator"

    @abstractmethod
    def validate(self, response: "HTTPResponseData") -> ValidationResult:  # type: ignore[name-defined]
        raise NotImplementedError
