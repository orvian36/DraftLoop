"""Flash-driven induced rule: 1-2 sentence portable rule per edit."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from draftloop_core.llm import GeminiClient

from draftloop_edits.types import ClassifiedEdit, EditClass, EditEvent, InducedRule

PROMPT = """An operator just edited a Case Fact Summary. Write a 1-2 sentence
PORTABLE rule (50-100 chars) that captures the underlying preference.

Before: {before}
After: {after}
Edit classes: {classes}

Return ONLY the rule text (no preamble, no quotes)."""


@dataclass
class RuleInducer:
    client: GeminiClient
    model: str

    def induce(self, evt: EditEvent, cls: ClassifiedEdit) -> InducedRule | None:
        induce_classes = {
            EditClass.FACT_CORRECTION,
            EditClass.CITATION_FIX,
            EditClass.TONE,
            EditClass.STRUCTURE,
        }
        if not induce_classes.intersection(cls.edit_class_labels):
            return None
        prompt = PROMPT.format(
            before=(evt.before or {}).get("text", ""),
            after=(evt.after or {}).get("text", ""),
            classes=",".join(c.value for c in cls.edit_class_labels),
        )
        resp = self.client.generate(model=self.model, contents=prompt)
        text = (resp.text or "").strip()
        if not text:
            return None
        rule_id = "rule_" + hashlib.sha1(f"{evt.event_id}|{text}".encode()).hexdigest()[:10]
        return InducedRule(
            rule_id=rule_id, event_id=evt.event_id, text=text,
            trust_weight=1.0, pinned=False, created_at=datetime.utcnow(),
        )
