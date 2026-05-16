"""Advisory critic — flags violations against active Principles."""

from __future__ import annotations

import json
from dataclasses import dataclass

from draftloop_core.llm import GeminiClient
from draftloop_drafting.schema import CaseFactSummary

from draftloop_edits.types import CritiqueResult

PROMPT = """You are a pre-ship critic for legal drafts. For each Fact below, decide:
(a) is the Fact supported by its citations? (b) does the Fact violate any Principle?

Return ONLY a JSON array: [{{"fact_id": str, "supported": bool, "violations": [str], "suggested_rewrite": str|null}}]

Principles:
{principles}

Facts:
{facts}
"""


@dataclass
class CritiqueRunner:
    client: GeminiClient
    model: str

    def review(self, summary: CaseFactSummary, principles: list[str]) -> list[CritiqueResult]:
        facts: list[dict] = []
        for slot_facts in summary.model_dump().values():
            facts.extend(slot_facts)
        listing = "\n".join(
            f"[{f['sentence_id']}] {f['text']} <citations: {[c['chunk_id'] for c in f['citations']]}>"
            for f in facts
        )
        resp = self.client.generate(
            model=self.model,
            contents=PROMPT.format(
                principles="\n".join(f"- {p}" for p in principles) or "(none)",
                facts=listing,
            ),
            config={"response_mime_type": "application/json"},
        )
        try:
            data = json.loads(resp.text)
        except Exception:
            return []
        return [
            CritiqueResult(
                fact_id=item["fact_id"],
                supported=bool(item.get("supported", True)),
                violations=list(item.get("violations") or []),
                suggested_rewrite=item.get("suggested_rewrite"),
            )
            for item in data
        ]
