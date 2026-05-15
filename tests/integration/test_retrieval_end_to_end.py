"""End-to-end retrieval: ingest synthetic complaint -> index -> query each slot.

Skipped when GEMINI_API_KEY is unset or is a known sentinel value (sk-test/demo*).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _has_real_key() -> bool:
    key = os.environ.get("GEMINI_API_KEY", "")
    return bool(key) and not key.startswith(("sk-test", "demo", "test"))


pytestmark = pytest.mark.skipif(
    not _has_real_key(),
    reason="needs real GEMINI_API_KEY for live retrieval e2e",
)


async def test_retrieval_e2e(tmp_path):
    from draftloop_core.config import get_settings
    from draftloop_core.llm import GeminiClient
    from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex
    from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex
    from draftloop_ingest import IngestPipeline, IngestRequest
    from draftloop_retrieval.embedder import GeminiEmbedder
    from draftloop_retrieval.indexer import Indexer
    from draftloop_retrieval.query_planner import QueryPlanner
    from draftloop_retrieval.reranker import FlashReranker
    from draftloop_retrieval.retriever import HybridRetriever
    from draftloop_retrieval.slot_plan import SLOT_PLAN
    from draftloop_retrieval.types import Chunk

    get_settings.cache_clear()
    settings = get_settings()
    client = GeminiClient()

    import build_synthetic_corpus as gen
    pdfs = gen.build(force=False)
    complaint = next(p for p in pdfs if p.name == "complaint.pdf")

    ingest = IngestPipeline().run(IngestRequest(matter_id="M-1", source_path=str(complaint)))

    vec_index = ChromaVectorIndex(persist_path=str(tmp_path / "chroma"))
    bm25_index = RankBm25LexicalIndex(persist_path=str(tmp_path / "bm25"))
    indexer = Indexer(
        vec_index=vec_index, bm25_index=bm25_index, client=client,
        embed_model=settings.embed_model, embed_dim=settings.embed_dim,
        prefix_model=settings.extraction_model,
    )
    await indexer.index(matter_id="M-1", ingest=ingest)

    def loader(ids: list[str]) -> dict[str, Chunk]:
        col = vec_index._collection("M-1")
        got = col.get(ids=ids, include=["documents", "metadatas"])
        result: dict[str, Chunk] = {}
        for i, cid in enumerate(got["ids"]):
            md = got["metadatas"][i]
            result[cid] = Chunk(
                chunk_id=cid, doc_id=md["doc_id"], matter_id="M-1",
                page=md["page"], section_label=md.get("section_label") or None,
                para_id=None,
                char_start=md["char_start"], char_end=md["char_end"],
                text=got["documents"][i], context_prefix="",
                embedding_text=got["documents"][i], embedding_dim=1536,
                confidence_min=md["confidence_min"],
                contains_needs_review=md["contains_needs_review"],
                ingest_version=md["ingest_version"],
            )
        return result

    embedder = GeminiEmbedder(client=client, model=settings.embed_model, dim=settings.embed_dim)
    planner = QueryPlanner(client=client, model=settings.extraction_model, n=3)
    reranker = FlashReranker(client=client, model=settings.extraction_model)

    retriever = HybridRetriever(
        vec_index=vec_index, bm25_index=bm25_index, embedder=embedder,
        planner=planner, reranker=reranker, chunk_loader=loader,
    )
    result = await retriever.retrieve(matter_id="M-1", slot_plan=SLOT_PLAN)
    assert any(len(hits) > 0 for hits in result.slots.values())
