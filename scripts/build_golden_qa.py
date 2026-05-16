#!/usr/bin/env python3
"""Generate a curated golden Q&A set for the synthetic corpus.

Writes ``data/golden/qa_v1.json``. v1 is hand-curated (~10 pairs across slots
+ 2 negative tests). A future script will use Flash to expand the set, with
human review on 20%.
"""

from __future__ import annotations

import json
from pathlib import Path

QA_V1 = [
    {
        "qa_id": "qa_parties_1",
        "slot": "parties",
        "question": "Who is the plaintiff?",
        "expected_fact_text": "Acme Corp.",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_parties_2",
        "slot": "parties",
        "question": "Who is the defendant?",
        "expected_fact_text": "Widgets Inc.",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_jur_1",
        "slot": "jurisdiction",
        "question": "Under what statute is jurisdiction claimed?",
        "expected_fact_text": "28 U.S.C. § 1331",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_dates_1",
        "slot": "key_dates",
        "question": "When was the SaaS agreement executed?",
        "expected_fact_text": "2024-03-14",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_dates_2",
        "slot": "key_dates",
        "question": "When is the motion to dismiss heard?",
        "expected_fact_text": "2026-06-15",
        "must_cite_chunk_ids": ["motion"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_claims_1",
        "slot": "claims",
        "question": "What is Count I?",
        "expected_fact_text": "Breach of Contract",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_relief_1",
        "slot": "relief_sought",
        "question": "What damages does plaintiff seek?",
        "expected_fact_text": "$250,000",
        "must_cite_chunk_ids": ["complaint"],
        "is_unsupported": False,
    },
    {
        "qa_id": "qa_post_1",
        "slot": "procedural_posture",
        "question": "What is the current procedural posture?",
        "expected_fact_text": "Motion to Dismiss pending",
        "must_cite_chunk_ids": ["motion"],
        "is_unsupported": False,
    },
    # NEGATIVE — deliberately not in corpus
    {
        "qa_id": "qa_neg_1",
        "slot": "key_evidence",
        "question": "What is the email evidence?",
        "expected_fact_text": "UNSUPPORTED",
        "must_cite_chunk_ids": [],
        "is_unsupported": True,
    },
    {
        "qa_id": "qa_neg_2",
        "slot": "key_dates",
        "question": "When was the trial held?",
        "expected_fact_text": "UNSUPPORTED",
        "must_cite_chunk_ids": [],
        "is_unsupported": True,
    },
]


def build_manifest() -> dict:
    """Compose a minimal manifest tying corpus documents to QA + truth stubs."""
    return {
        "version": "0.1.0",
        "documents": [
            {"doc_id": "complaint", "path": "complaint.pdf"},
            {"doc_id": "motion", "path": "motion.pdf"},
            {"doc_id": "answer", "path": "answer.pdf"},
            {"doc_id": "order", "path": "order.pdf"},
        ],
        "qa_set": QA_V1,
        "edit_streams": [],
        # ingest_truth markdown is filled by IngestSuite at run-time when it
        # extracts each synthetic PDF. For v1 we leave per-doc placeholder text.
        "ingest_truth": {
            doc_id: {"markdown": "", "needs_review_count": 0}
            for doc_id in ("complaint", "motion", "answer", "order")
        },
    }


def main() -> int:
    out_dir = Path("data/golden")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_v1.json").write_text(json.dumps(QA_V1, indent=2), encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps(build_manifest(), indent=2), encoding="utf-8")
    print(f"==> wrote {out_dir / 'qa_v1.json'}")
    print(f"==> wrote {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
