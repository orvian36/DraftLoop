"""TrustEngine — operator-level weighting with reversion demotion + recency."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ReversionEvent:
    reverter: str
    original_op: str
    sentence_id: str
    days_after: int


@dataclass
class TrustEngine:
    weights: dict[str, float] = field(default_factory=lambda: defaultdict(lambda: 1.0))
    reversions_against: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    reversions_caused: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    pinned_edits: dict[tuple[str, str], bool] = field(default_factory=dict)

    def record_edit(
        self,
        operator_id: str,
        sentence_id: str,
        text: str,
        ts: datetime,
        *,
        pinned: bool = False,
    ) -> None:
        if pinned:
            self.pinned_edits[(operator_id, sentence_id)] = True

    def record_reversion(self, event: ReversionEvent) -> None:
        if self.pinned_edits.get((event.original_op, event.sentence_id)):
            return
        if event.days_after > 7:
            return
        self.reversions_against[event.original_op] += 1
        self.reversions_caused[event.reverter] += 1
        self.weights[event.original_op] = max(
            0.0, self.weights[event.original_op] * 0.3
        )

    def score(self, operator_id: str):
        from draftloop_edits.types import TrustScore

        return TrustScore(
            operator_id=operator_id,
            agreement_score=1.0,
            reversions_against=self.reversions_against[operator_id],
            reversions_caused=self.reversions_caused[operator_id],
            current_weight=self.weights[operator_id],
            updated_at=datetime.utcnow(),
        )
