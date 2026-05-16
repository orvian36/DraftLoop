from unittest.mock import MagicMock

from draftloop_drafting.orchestrator import Drafter
from draftloop_drafting.schema import CaseFactSummary, Citation, Fact
from draftloop_drafting.types import DraftRequest, FactVerification


def test_drafter_end_to_end_with_mocks(tmp_path):
    summary = CaseFactSummary(
        parties=[
            Fact(
                sentence_id="s_1",
                text="X vs Y",
                citations=[Citation(chunk_id="c1", quote="X")],
                confidence="high",
            )
        ],
        jurisdiction=[],
        key_dates=[],
        claims=[],
        relief_sought=[],
        procedural_posture=[],
        key_evidence=[],
    )
    gen = MagicMock()
    gen.generate.return_value = (
        summary,
        MagicMock(input_tokens=100, output_tokens=20, cached_tokens=0),
    )
    ver = MagicMock()
    ver.verify_fact.return_value = FactVerification(
        sentence_id="s_1",
        substring_passed=True,
        hhem_score=0.9,
        llm_judge="skipped",
        final_verdict="pass",
        original_text=None,
        fail_reason=None,
    )
    writer = MagicMock()
    writer.write.return_value = str(tmp_path / "audit.json")
    asm = MagicMock()
    asm.render.return_value = ("system", "user")

    drafter = Drafter(
        prompt_assembler=asm,
        generator=gen,
        verifier=ver,
        audit_writer=writer,
    )
    req = DraftRequest(matter_id="M-1", draft_id="D-1", retrieval_hits={"parties": []})
    out = drafter.draft(req)
    assert out.summary == summary
    assert out.verification.summary.get("pass", 0) >= 1
    assert out.audit_trail_path.endswith("audit.json")
