"""Public types for draftloop_edits."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EditClass(StrEnum):
    FACT_CORRECTION = "fact_correction"
    CITATION_FIX = "citation_fix"
    TONE = "tone"
    STRUCTURE = "structure"
    ADDITION = "addition"
    DELETION = "deletion"


class EditEvent(BaseModel):
    event_id: str
    draft_id: str
    matter_id: str
    slot: str
    sentence_id: str | None
    op: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    source_evidence_ids: list[str] = Field(default_factory=list)
    word_diff: str | None = None
    time_to_edit_ms: int
    operator_id: str
    draft_model_version: str
    prompt_hash: str
    timestamp: str


class ClassifiedEdit(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    edit_class_labels: list[EditClass]
    classifier_confidences: dict[str, float]
    classifier_version: str
    classified_at: datetime


class InducedRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    event_id: str
    text: str
    trust_weight: float = 1.0
    pinned: bool = False
    created_at: datetime


class Exemplar(BaseModel):
    model_config = ConfigDict(frozen=True)

    edit_id: str
    induced_rule: str
    before_text: str | None
    after_text: str | None
    edit_class: list[EditClass]
    operator_id: str
    trust_weight: float
    age_days: int


class ExemplarBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_exemplars: list[Exemplar]
    style_exemplars: list[Exemplar]
    total_tokens: int


class Principle(BaseModel):
    model_config = ConfigDict(frozen=True)

    principle_id: str
    text: str
    source_rule_ids: list[str]
    status: Literal["active", "proposed", "retired"]
    coverage_count: int
    approved_at: datetime | None
    approved_by: str | None


class TrustScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    operator_id: str
    agreement_score: float
    reversions_against: int
    reversions_caused: int
    current_weight: float
    updated_at: datetime


class CritiqueResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str
    supported: bool
    violations: list[str]
    suggested_rewrite: str | None


class ReplayReport(BaseModel):
    report_id: str
    week_ending: str
    matters_replayed: int
    edit_distance_p50: float
    citation_retention_rate: float
    fact_jaccard_p50: float
    unsupported_rate: float
    per_matter: list[dict[str, Any]]
    generated_at: datetime
