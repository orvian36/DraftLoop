from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_retrieval.types import Chunk, RetrievalHit


def _hit(cid: str, slot: str = "claims") -> RetrievalHit:
    chunk = Chunk(
        chunk_id=cid,
        doc_id="d",
        matter_id="M-1",
        page=1,
        section_label="Claims",
        para_id=None,
        char_start=0,
        char_end=10,
        text="alleged breach",
        context_prefix="",
        embedding_text="x",
        embedding_dim=1536,
        confidence_min=0.9,
        contains_needs_review=False,
        ingest_version="v1",
    )
    return RetrievalHit(
        chunk=chunk,
        slot=slot,
        rerank_score=8.0,
        fusion_score=0.5,
        matched_query="q",
        retrieval_engines=["dense"],
        rank=1,
    )


def test_assembler_renders_chunks_with_ids():
    asm = PromptAssembler()
    system, user = asm.render(
        matter_id="M-1",
        retrieval_hits={"claims": [_hit("c1")]},
        fact_exemplars=[],
        style_exemplars=[],
        principles=[],
    )
    assert '<chunk id="c1"' in system
    assert "alleged breach" in system
    assert "matter M-1" in user


def test_assembler_renders_principles_and_exemplars():
    asm = PromptAssembler()
    system, _ = asm.render(
        matter_id="M-1",
        retrieval_hits={"claims": [_hit("c1")]},
        fact_exemplars=[
            {
                "induced_rule": "Use ISO dates",
                "before_text": "March 14, 2024",
                "after_text": "2024-03-14",
            }
        ],
        style_exemplars=[
            {
                "induced_rule": "Formal voice",
                "before_text": "Plaintiff said",
                "after_text": "Plaintiff alleges",
            }
        ],
        principles=["Always cite section numbers"],
    )
    assert "Use ISO dates" in system
    assert "Formal voice" in system
    assert "Always cite section numbers" in system


def test_assembler_dedupes_chunks_across_slots():
    asm = PromptAssembler()
    hit = _hit("c1")
    system, _ = asm.render(
        matter_id="M-1",
        retrieval_hits={"claims": [hit], "parties": [hit]},
        fact_exemplars=[],
        style_exemplars=[],
        principles=[],
    )
    assert system.count('id="c1"') == 1
