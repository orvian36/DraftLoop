from unittest.mock import AsyncMock, MagicMock

from draftloop_core.storage import VectorHit
from draftloop_core.storage.rank_bm25_lexical_index import LexicalHit
from draftloop_retrieval.reranker import RerankedItem
from draftloop_retrieval.retriever import HybridRetriever
from draftloop_retrieval.slot_plan import SLOT_PLAN
from draftloop_retrieval.types import Chunk


def _chunk(cid: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id="d",
        matter_id="M-1",
        page=1,
        section_label=None,
        para_id=None,
        char_start=0,
        char_end=10,
        text=f"text {cid}",
        context_prefix="",
        embedding_text=f"text {cid}",
        embedding_dim=1536,
        confidence_min=1.0,
        contains_needs_review=False,
        ingest_version="v1",
    )


async def test_retriever_runs_full_pipeline_per_slot():
    vec_index = AsyncMock()
    bm25_index = MagicMock()
    embedder = MagicMock()
    planner = MagicMock()
    reranker = MagicMock()

    planner.plan.return_value = {slot.name: [f"q {slot.name}"] for slot in SLOT_PLAN}
    embedder.embed_queries.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
    vec_index.search.return_value = [VectorHit(id="c1", score=0.9, metadata={})]
    bm25_index.search.return_value = [LexicalHit(id="c1", score=5.0, text="text c1")]
    reranker.rerank.return_value = [RerankedItem(index=0, score=8.0)]

    def loader(ids):
        return {i: _chunk(i) for i in ids}

    retriever = HybridRetriever(
        vec_index=vec_index,
        bm25_index=bm25_index,
        embedder=embedder,
        planner=planner,
        reranker=reranker,
        chunk_loader=loader,
        rrf_k=60,
        dense_top=10,
        bm25_top=10,
        rerank_top=5,
    )
    result = await retriever.retrieve(matter_id="M-1", slot_plan=SLOT_PLAN)
    assert set(result.slots.keys()) == {s.name for s in SLOT_PLAN}
    assert all(len(hits) >= 1 for hits in result.slots.values())
    # Each hit carries provenance from both engines.
    first = next(iter(result.slots.values()))[0]
    assert "dense" in first.retrieval_engines
    assert "bm25" in first.retrieval_engines


async def test_retriever_empty_fusion_returns_empty_slot():
    vec_index = AsyncMock()
    bm25_index = MagicMock()
    embedder = MagicMock()
    planner = MagicMock()
    reranker = MagicMock()

    planner.plan.return_value = {slot.name: ["q"] for slot in SLOT_PLAN}
    embedder.embed_queries.side_effect = lambda texts: [[0.0] * 1536 for _ in texts]
    vec_index.search.return_value = []
    bm25_index.search.return_value = []
    reranker.rerank.return_value = []

    retriever = HybridRetriever(
        vec_index=vec_index,
        bm25_index=bm25_index,
        embedder=embedder,
        planner=planner,
        reranker=reranker,
        chunk_loader=lambda ids: {},
    )
    result = await retriever.retrieve(matter_id="M-1", slot_plan=SLOT_PLAN[:2])
    assert all(hits == [] for hits in result.slots.values())
