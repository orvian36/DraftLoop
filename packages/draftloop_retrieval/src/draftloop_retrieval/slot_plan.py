"""The seven fact slots for the Case Fact Summary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    name: str
    intent: str


SLOT_PLAN: list[Slot] = [
    Slot("parties", "Who are the named parties, their roles, and counsel?"),
    Slot("jurisdiction", "Court, venue, jurisdiction basis, governing law."),
    Slot("key_dates", "Filing date, incident date, contract date, hearings."),
    Slot("claims", "Causes of action / counts and against whom."),
    Slot("relief_sought", "Damages, injunctions, other remedies requested."),
    Slot("procedural_posture", "Current stage: pleading, discovery, motion, trial, appeal."),
    Slot("key_evidence", "Exhibits, declarations, statements relied on."),
]
