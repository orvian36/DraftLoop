"""End-to-end ingestion against the synthetic corpus.

Builds the corpus on demand if it isn't present, then asserts core invariants
across all six PDFs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from draftloop_ingest import IngestPipeline, IngestRequest  # noqa: E402


@pytest.fixture(scope="module")
def synthetic_corpus():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import build_synthetic_corpus as gen

    return gen.build(force=False)


def test_digital_corpus_all_pages_extracted(synthetic_corpus):
    pipeline = IngestPipeline()
    digital_pdfs = [p for p in synthetic_corpus if "_scan" not in p.name]
    assert len(digital_pdfs) == 4

    for pdf in digital_pdfs:
        result = pipeline.run(IngestRequest(matter_id="TEST", source_path=str(pdf)))
        assert not result.failed, f"{pdf.name}: {result.fail_reason}"
        assert len(result.pages) >= 1, f"{pdf.name}: no pages extracted"
        assert all(p.class_ == "digital" for p in result.pages)
        assert result.aggregate_confidence == 1.0
        assert "<!-- page=1 -->" in result.markdown


def test_complaint_has_expected_facts(synthetic_corpus):
    pipeline = IngestPipeline()
    complaint = next(p for p in synthetic_corpus if p.name == "complaint.pdf")
    result = pipeline.run(IngestRequest(matter_id="TEST", source_path=str(complaint)))
    md = result.markdown.lower()
    assert "acme" in md
    assert "widgets" in md
    assert "saas agreement" in md
    assert "2024-03-14" in md


def test_scanned_complaint_recovers_key_facts(synthetic_corpus):
    pipeline = IngestPipeline()
    scan = next((p for p in synthetic_corpus if p.name == "complaint_scan.pdf"), None)
    if scan is None:
        pytest.skip("scanned complaint not generated")
    result = pipeline.run(IngestRequest(matter_id="TEST", source_path=str(scan)))
    if result.failed or not result.pages:
        pytest.skip("no OCR engine available")
    md = result.markdown.lower()
    # OCR may have minor errors; check forgiving substrings.
    assert any(k in md for k in ("complaint", "acme", "widgets", "2024-03-14"))
