import json

from draftloop_drafting.audit_trail import AuditTrailWriter


def test_writes_audit_json(tmp_path):
    writer = AuditTrailWriter(root=str(tmp_path))
    path = writer.write(
        matter_id="M-1",
        draft_id="D-1",
        model="gemini-2.5-pro",
        drafter_mode="single_call",
        prompt_hash="abc",
        cache_name=None,
        retrieved_chunks=[
            {"chunk_id": "c1", "slot": "claims", "rerank_score": 8.0, "engines": ["dense"]}
        ],
        exemplars_used=[],
        style_rules_active=[],
        verification={"summary": {"pass": 5}},
        token_usage={"input": 1000, "output": 200, "cached": 0},
        cost_usd=0.05,
        duration_ms=4000,
        ingest_versions={"doc_1": "v1"},
    )
    with open(path) as f:
        data = json.load(f)
    assert data["matter_id"] == "M-1"
    assert data["model"] == "gemini-2.5-pro"
    assert data["retrieved_chunks"][0]["chunk_id"] == "c1"
