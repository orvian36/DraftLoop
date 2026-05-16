"""Slot -> 3-5 paraphrased queries (multi-query expansion)."""

from __future__ import annotations

import re

from draftloop_core.llm import GeminiClient

from draftloop_retrieval.slot_plan import Slot

PROMPT = """Generate {n} distinct paraphrases of the following retrieval intent.
Each paraphrase should be a self-contained question or noun phrase that could be
used to search a corpus of legal documents.

Intent: {intent}

Return as a numbered list. Do not add preamble.
"""


class QueryPlanner:
    def __init__(self, *, client: GeminiClient, model: str, n: int = 3) -> None:
        self._client = client
        self._model = model
        self._n = n

    def plan(self, slots: list[Slot]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for slot in slots:
            resp = self._client.generate(
                model=self._model,
                contents=PROMPT.format(n=self._n, intent=slot.intent),
            )
            phrases = self._parse(resp.text or "")
            if not phrases:
                phrases = [slot.intent]
            out[slot.name] = phrases[: self._n]
        return out

    @staticmethod
    def _parse(text: str) -> list[str]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        cleaned: list[str] = []
        for ln in lines:
            m = re.match(r"^(?:\d+[.)]\s+|-\s+)?(.*)$", ln)
            if m:
                phrase = m.group(1).strip()
                if phrase:
                    cleaned.append(phrase)
        return cleaned
