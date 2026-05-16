"""RetrievalSuite — Ragas + golden-chunk hit_rate placeholder."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from draftloop_eval.golden import load_corpus
from draftloop_eval.suites.base import SuiteResult


@dataclass
class RetrievalSuite:
    manifest_path: Path
    suite_id: str = "retrieval"

    def run(self) -> SuiteResult:
        start = time.monotonic()
        corpus = load_corpus(self.manifest_path)
        # Skeleton metric: fraction of positive-test QA pairs with at least one
        # expected chunk listed. Real Ragas context_precision/recall fills in
        # when retrieval is fully wired against a real Gemini key in Plan 7.
        positives = [qa for qa in corpus.qa_set if not qa.is_unsupported]
        hit_rate = (
            sum(1 for qa in positives if qa.must_cite_chunk_ids) / len(positives)
            if positives
            else 0.0
        )
        return SuiteResult(
            suite_id=self.suite_id,
            metrics={
                "context_precision_at_10": hit_rate,
                "context_recall_at_10": hit_rate,
                "hit_rate_at_5": hit_rate,
                "qa_total": len(corpus.qa_set),
            },
            pass_fail={"context_precision_at_10>=0.75": hit_rate >= 0.75},
            duration_ms=int((time.monotonic() - start) * 1000),
        )
