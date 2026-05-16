"""Public types for the drafting orchestrator."""

from __future__ import annotations

from typing import Any, Literal

from draftloop_retrieval.types import RetrievalHit
from pydantic import BaseModel, ConfigDict, Field

from draftloop_drafting.schema import CaseFactSummary


def _empty_exemplars() -> dict[str, list[dict[str, Any]]]:
    return {"fact": [], "style": []}


class DraftRequest(BaseModel):
    matter_id: str
    draft_id: str
    retrieval_hits: dict[str, list[RetrievalHit]]
    exemplars: dict[str, list[dict[str, Any]]] = Field(default_factory=_empty_exemplars)
    principles: list[str] = Field(default_factory=list)
    drafter_mode: Literal["single_call", "two_call"] = "single_call"
    drafter_model: str = "gemini-2.5-pro"
    extraction_model: str = "gemini-2.5-flash"


class FactVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentence_id: str
    substring_passed: bool
    hhem_score: float | None
    llm_judge: Literal["supported", "unsupported", "skipped"]
    final_verdict: Literal["pass", "rewrite_to_unsupported"]
    original_text: str | None
    fail_reason: str | None


class VerificationReport(BaseModel):
    matter_id: str
    draft_id: str
    fact_results: list[FactVerification]
    summary: dict[str, int]
    duration_ms: int


class DraftResult(BaseModel):
    matter_id: str
    draft_id: str
    summary: CaseFactSummary
    verification: VerificationReport
    audit_trail_path: str
    cost_usd: float
    duration_ms: int
    token_usage: dict[str, int]
