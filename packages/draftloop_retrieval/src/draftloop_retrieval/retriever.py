"""HybridRetriever — multi-query -> dense + BM25 -> RRF -> rerank -> top-k per slot."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from draftloop_core.storage import VectorIndex
from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex

from draftloop_retrieval.embedder import GeminiEmbedder
from draftloop_retrieval.query_planner import QueryPlanner
from draftloop_retrieval.reranker import Reranker
from draftloop_retrieval.rrf import rrf_fuse
from draftloop_retrieval.slot_plan import Slot
from draftloop_retrieval.types import Chunk, RetrievalHit, RetrievalResult


@dataclass
class HybridRetriever:
    vec_index: VectorIndex
    bm25_index: RankBm25LexicalIndex
    embedder: GeminiEmbedder
    planner: QueryPlanner
    reranker: Reranker
    chunk_loader: Callable[[list[str]], dict[str, Chunk]]
    rrf_k: int = 60
    dense_top: int = 50
    bm25_top: int = 50
    rerank_top: int = 15

    async def retrieve(self, *, matter_id: str, slot_plan: list[Slot]) -> RetrievalResult:
        start = time.monotonic()
        queries = self.planner.plan(slot_plan)
        slots_out: dict[str, list[RetrievalHit]] = {}

        for slot in slot_plan:
            paraphrases = queries.get(slot.name, [slot.intent])
            vectors = self.embedder.embed_queries(paraphrases)

            dense_rankings: list[list[tuple[str, float]]] = []
            for vec in vectors:
                hits = await self.vec_index.search(matter_id, vec, top_k=self.dense_top)
                dense_rankings.append([(h.id, h.score) for h in hits])

            bm25_rankings: list[list[tuple[str, float]]] = []
            for q in paraphrases:
                lex_hits = self.bm25_index.search(matter_id, q, top_k=self.bm25_top)
                bm25_rankings.append([(h.id, h.score) for h in lex_hits])

            fused = rrf_fuse(
                dense_rankings + bm25_rankings,
                k=self.rrf_k,
                top_k=self.dense_top,
                engine_names=["dense"] * len(dense_rankings) + ["bm25"] * len(bm25_rankings),
            )

            if not fused:
                slots_out[slot.name] = []
                continue

            ids_in_order = [f.id for f in fused]
            chunks_by_id = self.chunk_loader(ids_in_order)
            candidates_text = [chunks_by_id[i].text for i in ids_in_order if i in chunks_by_id]
            ranked = self.reranker.rerank(
                query=slot.intent, candidates=candidates_text, top_k=self.rerank_top,
            )

            hits_out: list[RetrievalHit] = []
            for rank, r in enumerate(ranked, start=1):
                if r.index >= len(ids_in_order):
                    continue
                cid = ids_in_order[r.index]
                if cid not in chunks_by_id:
                    continue
                fhit = fused[r.index]
                hits_out.append(
                    RetrievalHit(
                        chunk=chunks_by_id[cid],
                        slot=slot.name,
                        rerank_score=r.score,
                        fusion_score=fhit.score,
                        matched_query=paraphrases[0],
                        retrieval_engines=list(fhit.engines),  # type: ignore[arg-type]
                        rank=rank,
                    )
                )
            slots_out[slot.name] = hits_out

        return RetrievalResult(
            matter_id=matter_id,
            slots=slots_out,
            queries_used=queries,
            duration_ms=int((time.monotonic() - start) * 1000),
            cost_usd=0.0,
        )
