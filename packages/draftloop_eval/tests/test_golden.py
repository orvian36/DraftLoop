import json

from draftloop_eval.golden import GoldenQA, load_corpus


def test_golden_qa_negative_test_marker():
    qa = GoldenQA(
        qa_id="qa_1",
        slot="key_dates",
        question="When was the agreement executed?",
        expected_fact_text="2024-03-14",
        must_cite_chunk_ids=["c1"],
        is_unsupported=False,
    )
    assert qa.is_unsupported is False


def test_golden_corpus_load(tmp_path):
    manifest = {
        "version": "0.1.0",
        "documents": [{"doc_id": "complaint", "path": "complaint.pdf"}],
        "qa_set": [
            {
                "qa_id": "qa_1",
                "slot": "parties",
                "question": "Who are the parties?",
                "expected_fact_text": "Acme v. Widgets",
                "must_cite_chunk_ids": ["c1"],
                "is_unsupported": False,
            }
        ],
        "edit_streams": [],
        "ingest_truth": {"complaint": {"markdown": "...", "needs_review_count": 0}},
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    corpus = load_corpus(p)
    assert corpus.version == "0.1.0"
    assert len(corpus.documents) == 1
    assert corpus.qa_set[0].expected_fact_text == "Acme v. Widgets"
