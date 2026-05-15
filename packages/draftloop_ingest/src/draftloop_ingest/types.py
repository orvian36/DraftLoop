"""Public types for the ingestion package."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NEEDS_REVIEW_THRESHOLD = 0.80

EngineName = Literal[
    "pymupdf4llm",
    "paddleocr",
    "tesseract",
    "gemini_vision",
    "trocr",
]
PageClass = Literal[
    "digital", "clean_scan", "low_res", "handwritten", "photo", "mixed"
]
ReviewReason = Literal["low_ocr_conf", "illegible", "blurry", "redacted"]


class DocStatus(StrEnum):
    UPLOADED = "uploaded"
    PROBING = "probing"
    EXTRACTING = "extracting"
    RASTERIZING = "rasterizing"
    CLASSIFYING = "classifying"
    PREPROCESSING = "preprocessing"
    OCR_RUNNING = "ocr_running"
    VERIFYING = "verifying"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class Line(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float = Field(..., ge=0.0, le=1.0)
    engine: EngineName
    needs_review: bool = False

    @model_validator(mode="after")
    def _enforce_review_invariant(self) -> Line:
        # Force needs_review := confidence < threshold (no caller override).
        object.__setattr__(self, "needs_review", self.confidence < NEEDS_REVIEW_THRESHOLD)
        return self


class NeedsReviewSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[int, int, int, int]
    text: str
    confidence: float
    reason: ReviewReason


class Page(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    width_px: int
    height_px: int
    dpi: int
    class_: PageClass
    engines_used: list[EngineName]
    lines: list[Line]
    needs_review: bool


class IngestRequest(BaseModel):
    matter_id: str
    source_path: str
    doc_id: str | None = None
    enable_paddle: bool = True
    enable_tesseract_fallback: bool = True


class IngestResult(BaseModel):
    doc_id: str
    source_path: str
    pages: list[Page]
    markdown: str
    needs_review_spans: list[NeedsReviewSpan]
    aggregate_confidence: float
    engines_used: dict[int, list[EngineName]]
    duration_ms: int
    ingest_version: str
    failed: bool = False
    fail_reason: str | None = None
