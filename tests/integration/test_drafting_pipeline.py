"""End-to-end drafting with mocked Gemini.

Verifies orchestrator wiring + verifier behavior against a planted-bad-citation case.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from draftloop_drafting.audit_trail import AuditTrailWriter
from draftloop_drafting.generator import Generator
from draftloop_drafting.orchestrator import Drafter
from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_drafting.schema import UNSUPPORTED, CaseFactSummary, Citation, Fact
from draftloop_drafting.types import DraftRequest
from draftloop_drafting.verifier import Verifier
from draftloop_retrieval.types import Chunk, RetrievalHit


def _hit(cid: str, text: str) -> RetrievalHit:
    chunk = Chunk(
        chunk_id=cid, doc_id="d", matter_id="M-1", page=1, section_label="Claims",
        para_id=None, char_start=0, char_end=len(text), text=text,
        context_prefix="", embedding_text=text, embedding_dim=1536,
        confidence_min=1.0, contains_needs_review=False, ingest_version="v1",
    )
    return RetrievalHit(
        chunk=chunk, slot="claims", rerank_score=8.0, fusion_score=0.5,
        matched_query="q", retrieval_engines=["dense"], rank=1,
    )


def test_planted_bad_citation_rewrites_to_unsupported(tmp_path):
    """A Fact whose Citation.quote is NOT in the chunk must be rewritten to UNSUPPORTED."""
    bad = CaseFactSummary(
        parties=[], jurisdiction=[], key_dates=[], claims=[
            Fact(sentence_id="s_1", text="Defendant denies.",
                 citations=[Citation(chunk_id="c1", quote="Plaintiff was on Mars")],
                 confidence="high")
        ],
        relief_sought=[], procedural_posture=[], key_evidence=[],
    )
    gen = MagicMock()
    gen.generate.return_value = (bad, MagicMock(input_tokens=100, output_tokens=20, cached_tokens=0))

    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.9  # high — but substring check should fail first
    fake_judge = MagicMock()
    fake_judge.generate.return_value = MagicMock(text="UNSUPPORTED")
    verifier = Verifier(hhem=fake_hhem, judge=fake_judge, judge_model="gemini-2.5-flash")

    drafter = Drafter(
        prompt_assembler=PromptAssembler(),
        generator=gen,
        verifier=verifier,
        audit_writer=AuditTrailWriter(root=str(tmp_path)),
    )
    req = DraftRequest(
        matter_id="M-1", draft_id="D-1",
        retrieval_hits={"claims": [_hit("c1", "Defendant denies.")]},
    )
    result = drafter.draft(req)
    only_claim = result.summary.claims[0]
    assert only_claim.text == UNSUPPORTED
    assert only_claim.citations == []


def test_well_grounded_fact_passes_through(tmp_path):
    """A Fact whose quote IS a substring of the chunk and HHEM scores high passes."""
    good = CaseFactSummary(
        parties=[Fact(sentence_id="s_1", text="Acme v. Widgets",
                      citations=[Citation(chunk_id="c1", quote="Acme")],
                      confidence="high")],
        jurisdiction=[], key_dates=[], claims=[],
        relief_sought=[], procedural_posture=[], key_evidence=[],
    )
    gen = MagicMock()
    gen.generate.return_value = (good, MagicMock(input_tokens=100, output_tokens=20, cached_tokens=0))
    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.95
    verifier = Verifier(hhem=fake_hhem, judge=MagicMock(), judge_model="gemini-2.5-flash")

    drafter = Drafter(
        prompt_assembler=PromptAssembler(),
        generator=gen,
        verifier=verifier,
        audit_writer=AuditTrailWriter(root=str(tmp_path)),
    )
    req = DraftRequest(
        matter_id="M-1", draft_id="D-1",
        retrieval_hits={"parties": [_hit("c1", "Acme Corp. brings this action.")]},
    )
    result = drafter.draft(req)
    assert result.summary.parties[0].text == "Acme v. Widgets"
    assert result.verification.summary.get("pass", 0) >= 1
