"""Indexer — orchestrates: split -> prefix -> embed -> upsert + BM25 add."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_core.llm import GeminiClient
from draftloop_core.storage import VectorIndex, VectorItem
from draftloop_core.storage.rank_bm25_lexical_index import LexicalDoc, RankBm25LexicalIndex

from draftloop_ingest.types import IngestResult
from draftloop_retrieval.embedder import GeminiEmbedder
from draftloop_retrieval.prefixer import ContextualPrefixer
from draftloop_retrieval.splitter import StructuralSplitter
from draftloop_retrieval.types import Chunk


@dataclass(frozen=True)
class IndexResult:
    matter_id: str
    doc_id: str
    chunks_indexed: int


class Indexer:
    def __init__(
        self,
        *,
        vec_index: VectorIndex,
        bm25_index: RankBm25LexicalIndex,
        client: GeminiClient,
        embed_model: str,
        embed_dim: int,
        prefix_model: str,
        splitter: StructuralSplitter | None = None,
    ) -> None:
        self._vec_index = vec_index
        self._bm25_index = bm25_index
        self._client = client
        self._embedder = GeminiEmbedder(client=client, model=embed_model, dim=embed_dim)
        self._prefixer = ContextualPrefixer(client=client, model=prefix_model)
        self._splitter = splitter or StructuralSplitter()

    async def index(self, *, matter_id: str, ingest: IngestResult) -> IndexResult:
        chunks: list[Chunk] = list(
            self._splitter.split(
                markdown=ingest.markdown,
                doc_id=ingest.doc_id,
                matter_id=matter_id,
                ingest_version=ingest.ingest_version,
            )
        )
        if not chunks:
            return IndexResult(matter_id=matter_id, doc_id=ingest.doc_id, chunks_indexed=0)

        prefixed = self._prefixer.prefix(chunks)
        vectors = self._embedder.embed_documents([c.embedding_text for c in prefixed])
        items = [
            VectorItem(
                id=c.chunk_id,
                vector=vectors[i],
                metadata={
                    "matter_id": matter_id,
                    "doc_id": c.doc_id,
                    "page": c.page,
                    "section_label": c.section_label or "",
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "confidence_min": c.confidence_min,
                    "contains_needs_review": c.contains_needs_review,
                    "ingest_version": c.ingest_version,
                },
                document=c.text,
            )
            for i, c in enumerate(prefixed)
        ]
        await self._vec_index.upsert(matter_id, items)
        self._bm25_index.add(
            matter_id,
            [LexicalDoc(id=c.chunk_id, text=c.context_prefix + " " + c.text) for c in prefixed],
        )
        return IndexResult(matter_id=matter_id, doc_id=ingest.doc_id, chunks_indexed=len(prefixed))
