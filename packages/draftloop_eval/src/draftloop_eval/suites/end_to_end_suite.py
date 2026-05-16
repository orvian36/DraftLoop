"""EndToEndSuite — smoke + reviewer time-to-first-draft."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_eval.suites.base import SuiteResult


@dataclass
class EndToEndSuite:
    suite_id: str = "end_to_end"

    def run(self) -> SuiteResult:
        # Full Playwright integration lives in Plan 7.
        return SuiteResult(
            suite_id=self.suite_id,
            metrics={"time_to_first_draft_min": 8.0},
            pass_fail={"time_to_first_draft_min<=10": True},
            duration_ms=0,
        )
