"""CaseFactSummary schema with structural grounding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

UNSUPPORTED = "UNSUPPORTED"


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    quote: str = Field(..., max_length=240)


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentence_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

    @model_validator(mode="after")
    def _enforce_grounding(self) -> Fact:
        if self.text == UNSUPPORTED:
            return self
        if len(self.citations) < 1:
            raise ValueError(
                f"Fact {self.sentence_id!r}: requires >=1 Citation or text=UNSUPPORTED"
            )
        return self


class CaseFactSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    parties: list[Fact]
    jurisdiction: list[Fact]
    key_dates: list[Fact]
    claims: list[Fact]
    relief_sought: list[Fact]
    procedural_posture: list[Fact]
    key_evidence: list[Fact]
