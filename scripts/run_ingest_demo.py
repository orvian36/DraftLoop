#!/usr/bin/env python3
"""One-PDF demo: run IngestPipeline and print Markdown + confidence summary."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "demo-not-used")

from draftloop_ingest import IngestPipeline, IngestRequest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--json", action="store_true", help="Emit IngestResult JSON")
    args = parser.parse_args()

    pipeline = IngestPipeline()
    result = pipeline.run(
        IngestRequest(matter_id="DEMO", source_path=str(Path(args.pdf).resolve()))
    )

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"doc_id            : {result.doc_id}")
    print(f"pages             : {len(result.pages)}")
    print(f"engines_used      : {result.engines_used}")
    print(f"aggregate_conf    : {result.aggregate_confidence:.3f}")
    print(f"needs_review spans: {len(result.needs_review_spans)}")
    print(f"duration_ms       : {result.duration_ms}")
    print()
    print("---- Markdown ----")
    print(result.markdown)
    return 0 if not result.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
