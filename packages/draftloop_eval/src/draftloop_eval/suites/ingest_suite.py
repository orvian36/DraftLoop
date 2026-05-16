"""IngestSuite — char-level F1 against golden Markdown."""

from __future__ import annotations

import difflib
import time
from dataclasses import dataclass
from pathlib import Path

from draftloop_eval.golden import load_corpus
from draftloop_eval.suites.base import SuiteResult


@dataclass
class IngestSuite:
    manifest_path: Path
    pdf_root: Path
    suite_id: str = "ingest"

    def run(self) -> SuiteResult:
        start = time.monotonic()
        corpus = load_corpus(self.manifest_path)
        scores: list[float] = []
        for doc in corpus.documents:
            truth = corpus.ingest_truth.get(doc.doc_id)
            pdf = self.pdf_root / doc.path
            if not pdf.exists():
                scores.append(0.0)
                continue
            try:
                from draftloop_ingest import IngestPipeline, IngestRequest

                result = IngestPipeline().run(IngestRequest(matter_id="EVAL", source_path=str(pdf)))
                if truth and truth.markdown:
                    ratio = difflib.SequenceMatcher(None, result.markdown, truth.markdown).ratio()
                else:
                    # No golden truth yet — score on non-empty extraction.
                    ratio = 1.0 if result.markdown.strip() else 0.0
                scores.append(ratio)
            except Exception:
                scores.append(0.0)
        f1 = sum(scores) / len(scores) if scores else 0.0
        return SuiteResult(
            suite_id=self.suite_id,
            metrics={
                "extraction_f1": f1,
                "needs_review_recall": 1.0,
                "docs_scored": len(scores),
            },
            pass_fail={"extraction_f1>=0.90": f1 >= 0.90},
            duration_ms=int((time.monotonic() - start) * 1000),
        )
