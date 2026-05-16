from draftloop_retrieval.slot_plan import SLOT_PLAN, Slot
from draftloop_retrieval.types import Chunk, RetrievalHit


def test_chunk_carries_offsets():
    c = Chunk(
        chunk_id="doc_3_p4_c_0012",
        doc_id="doc_3",
        matter_id="M-001",
        page=4,
        section_label="Claims",
        para_id="¶12",
        char_start=1822,
        char_end=1987,
        text="Plaintiff alleges breach.",
        context_prefix="From the Complaint, Section II, ¶12.",
        embedding_text="From the Complaint, Section II, ¶12.\n\nPlaintiff alleges breach.",
        embedding_dim=1536,
        confidence_min=0.95,
        contains_needs_review=False,
        ingest_version="v1",
    )
    assert c.char_start < c.char_end


def test_slot_plan_has_seven_slots():
    assert len(SLOT_PLAN) == 7
    assert all(isinstance(s, Slot) for s in SLOT_PLAN)
    assert {s.name for s in SLOT_PLAN} == {
        "parties",
        "jurisdiction",
        "key_dates",
        "claims",
        "relief_sought",
        "procedural_posture",
        "key_evidence",
    }


def test_retrieval_hit_carries_provenance():
    chunk = Chunk(
        chunk_id="x",
        doc_id="d",
        matter_id="M-1",
        page=1,
        section_label=None,
        para_id=None,
        char_start=0,
        char_end=10,
        text="x",
        context_prefix="",
        embedding_text="x",
        embedding_dim=1536,
        confidence_min=1.0,
        contains_needs_review=False,
        ingest_version="v1",
    )
    hit = RetrievalHit(
        chunk=chunk,
        slot="claims",
        rerank_score=8.4,
        fusion_score=0.5,
        matched_query="q",
        retrieval_engines=["dense", "bm25"],
        rank=1,
    )
    assert "dense" in hit.retrieval_engines and "bm25" in hit.retrieval_engines
