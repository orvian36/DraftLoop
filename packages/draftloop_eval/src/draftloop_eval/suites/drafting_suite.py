"""DraftingSuite — Ragas faithfulness + HHEM + abstention placeholder."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from draftloop_eval.golden import load_corpus
from draftloop_eval.suites.base import SuiteResult


@dataclass
class DraftingSuite:
    manifest_path: Path
    suite_id: str = "drafting"

    def run(self) -> SuiteResult:
        start = time.monotonic()
        corpus = load_corpus(self.manifest_path)
        n_neg = sum(1 for qa in corpus.qa_set if qa.is_unsupported)
        n_pos = len(corpus.qa_set) - n_neg
        # Skeleton metrics — real Ragas faithfulness scoring requires a Gemini
        # key and live draft generation, added when running the full eval.
        return SuiteResult(
            suite_id=self.suite_id,
            metrics={
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "hhem_mean": 0.0,
                "abstention_precision": 1.0,
                "abstention_recall": 0.0,
                "positives": n_pos,
                "negatives": n_neg,
            },
            pass_fail={"faithfulness>=0.85": False},
            duration_ms=int((time.monotonic() - start) * 1000),
        )
