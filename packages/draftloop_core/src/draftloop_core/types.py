"""Shared base types used across all draftloop_* packages.

Anything imported by two or more packages MUST live here, per CLAUDE.md §1.3.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field

MatterId = NewType("MatterId", str)
DocId = NewType("DocId", str)
ChunkId = NewType("ChunkId", str)
DraftId = NewType("DraftId", str)
EditEventId = NewType("EditEventId", str)
OperatorId = NewType("OperatorId", str)
RuleId = NewType("RuleId", str)
PrincipleId = NewType("PrincipleId", str)

NEEDS_REVIEW_THRESHOLD = 0.80


class RetrievalEngine(StrEnum):
    DENSE = "dense"
    BM25 = "bm25"


class EditClass(StrEnum):
    FACT_CORRECTION = "fact_correction"
    CITATION_FIX = "citation_fix"
    TONE = "tone"
    STRUCTURE = "structure"
    ADDITION = "addition"
    DELETION = "deletion"


class NeedsReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_review: bool

    @classmethod
    def from_confidence(cls, confidence: float) -> NeedsReview:
        return cls(
            confidence=confidence,
            needs_review=confidence < NEEDS_REVIEW_THRESHOLD,
        )


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: float
    currency: str = "USD"

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(
                f"cannot add Money in different currencies: {self.currency} vs {other.currency}"
            )
        return Money(amount=self.amount + other.amount, currency=self.currency)
