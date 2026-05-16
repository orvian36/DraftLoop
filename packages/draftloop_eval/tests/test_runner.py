import json
from pathlib import Path

from draftloop_eval.runner import EvalRunner


def _write_manifest(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps(
            {
                "version": "0.1.0",
                "documents": [],
                "qa_set": [
                    {
                        "qa_id": "q1",
                        "slot": "parties",
                        "question": "?",
                        "expected_fact_text": "x",
                        "must_cite_chunk_ids": ["c1"],
                        "is_unsupported": False,
                    }
                ],
                "edit_streams": [],
                "ingest_truth": {},
            }
        )
    )
    return p


def test_runner_aggregates_all_suites(tmp_path):
    runner = EvalRunner(manifest_path=_write_manifest(tmp_path), pdf_root=tmp_path)
    report = runner.run()
    assert "ingest" in report.suites
    assert "retrieval" in report.suites
    assert "drafting" in report.suites
    assert "improvement" in report.suites
    assert "end_to_end" in report.suites
    assert "cost_budget" in report.suites


def test_runner_honors_suite_filter(tmp_path):
    runner = EvalRunner(manifest_path=_write_manifest(tmp_path), pdf_root=tmp_path)
    report = runner.run(suites=["retrieval"])
    assert set(report.suites.keys()) == {"retrieval"}
