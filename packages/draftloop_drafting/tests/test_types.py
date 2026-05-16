from draftloop_drafting.types import (
    DraftRequest,
    FactVerification,
    VerificationReport,
)


def test_draft_request_minimum_fields():
    req = DraftRequest(matter_id="M-1", draft_id="D-1", retrieval_hits={"claims": []})
    assert req.drafter_mode == "single_call"
    assert req.drafter_model == "gemini-2.5-pro"
    assert req.exemplars == {"fact": [], "style": []}
    assert req.principles == []


def test_verification_report_summary():
    fv = FactVerification(
        sentence_id="s_1",
        substring_passed=True,
        hhem_score=0.9,
        llm_judge="skipped",
        final_verdict="pass",
        original_text=None,
        fail_reason=None,
    )
    report = VerificationReport(
        matter_id="M-1",
        draft_id="D-1",
        fact_results=[fv],
        summary={"pass": 1},
        duration_ms=10,
    )
    assert report.summary["pass"] == 1
