import json
from pathlib import Path

from draftloop_eval.suites.ingest_suite import IngestSuite


def test_ingest_suite_runs_against_corpus(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "0.1.0",
                "documents": [{"doc_id": "dummy", "path": "dummy.pdf"}],
                "qa_set": [],
                "edit_streams": [],
                "ingest_truth": {"dummy": {"markdown": "dummy", "needs_review_count": 0}},
            }
        )
    )
    suite = IngestSuite(manifest_path=manifest_path, pdf_root=tmp_path)
    result = suite.run()
    assert "extraction_f1" in result.metrics
    assert result.metrics["docs_scored"] == 1
