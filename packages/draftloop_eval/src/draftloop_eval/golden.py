"""Golden corpus + Q&A + simulated edit streams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from draftloop_edits.types import EditEvent


class GoldenDoc(BaseModel):
    doc_id: str
    path: str


class GoldenIngestTruth(BaseModel):
    markdown: str
    needs_review_count: int = 0


class GoldenQA(BaseModel):
    qa_id: str
    slot: str
    question: str
    expected_fact_text: str
    must_cite_chunk_ids: list[str]
    is_unsupported: bool = False


class GoldenEditWeek(BaseModel):
    week_index: int
    events: list[EditEvent]


class GoldenEditStream(BaseModel):
    operator_id: str
    intent: Literal["aligned", "noisy"]
    weeks: list[GoldenEditWeek] = Field(default_factory=list)


class GoldenCorpus(BaseModel):
    version: str
    documents: list[GoldenDoc]
    qa_set: list[GoldenQA]
    edit_streams: list[GoldenEditStream]
    ingest_truth: dict[str, GoldenIngestTruth]


def load_corpus(manifest_path: Path) -> GoldenCorpus:
    raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return GoldenCorpus.model_validate(raw)
