"""Common Suite types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SuiteResult:
    suite_id: str
    metrics: dict[str, Any]
    pass_fail: dict[str, bool]
    duration_ms: int


class Suite(Protocol):
    suite_id: str

    def run(self) -> SuiteResult: ...
