"""CostBudgetSuite — VCR-cassette regression gate (placeholder)."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_eval.suites.base import SuiteResult


@dataclass
class CostBudgetSuite:
    suite_id: str = "cost_budget"
    budget_usd: float = 2.0

    def run(self) -> SuiteResult:
        # Real implementation replays VCR cassettes and counts tokens × prices.
        return SuiteResult(
            suite_id=self.suite_id,
            metrics={"recorded_cost_usd": 0.0, "budget_usd": self.budget_usd},
            pass_fail={"under_budget": True},
            duration_ms=0,
        )
