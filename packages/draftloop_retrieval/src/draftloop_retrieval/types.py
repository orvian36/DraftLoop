"""Public types for the retrieval package."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    doc_id: str
    matter_id: str
    page: int
    section_label: str | None
    para_id: str | None
    char_start: int
    char_end: int
    text: str
    context_prefix: str
    embedding_text: str
    embedding_dim: int
    confidence_min: float = Field(..., ge=0.0, le=1.0)
    contains_needs_review: bool
    ingest_version: str


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    slot: str
    paraphrases: list[str]


class RetrievalHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    slot: str
    rerank_score: float
    fusion_score: float
    matched_query: str
    retrieval_engines: list[Literal["dense", "bm25"]]
    rank: int


class RetrievalResult(BaseModel):
    matter_id: str
    slots: dict[str, list[RetrievalHit]]
    queries_used: dict[str, list[str]]
    duration_ms: int
    cost_usd: float
