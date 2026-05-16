"""Hybrid EditClassifier — deterministic rules first, Flash as fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

from draftloop_core.llm import GeminiClient

from draftloop_edits.types import ClassifiedEdit, EditClass, EditEvent

_DATE_RE = re.compile(
    r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b"
)
_NUMBER_RE = re.compile(r"\b\d+(?:[,.]\d+)*\b")

CLASSIFIER_VERSION = "v1"


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


@dataclass
class EditClassifier:
    flash_client: GeminiClient
    flash_model: str

    def classify(self, evt: EditEvent) -> ClassifiedEdit:
        labels = self._deterministic(evt)
        if not labels:
            labels, conf = self._flash(evt)
        else:
            conf = {lbl.value: 1.0 for lbl in labels}
        return ClassifiedEdit(
            event_id=evt.event_id,
            edit_class_labels=labels,
            classifier_confidences=conf,
            classifier_version=CLASSIFIER_VERSION,
            classified_at=datetime.utcnow(),
        )

    def _deterministic(self, evt: EditEvent) -> list[EditClass]:
        before_text = (evt.before or {}).get("text", "") or ""
        after_text = (evt.after or {}).get("text", "") or ""
        before_cits = {c["chunk_id"] for c in ((evt.before or {}).get("citations") or [])}
        after_cits = {c["chunk_id"] for c in ((evt.after or {}).get("citations") or [])}

        if evt.op == "fact_added":
            return [EditClass.ADDITION]
        if evt.op in ("fact_deleted", "fact_marked_unsupported"):
            return [EditClass.DELETION]

        labels: list[EditClass] = []
        if (
            before_text
            and after_text
            and before_cits == after_cits
            and _norm(before_text) != _norm(after_text)
        ):
            if set(_DATE_RE.findall(before_text)) != set(_DATE_RE.findall(after_text)) or set(
                _NUMBER_RE.findall(before_text)
            ) != set(_NUMBER_RE.findall(after_text)):
                labels.append(EditClass.FACT_CORRECTION)
            if _strip_ws(before_text) == _strip_ws(after_text):
                labels.append(EditClass.TONE)

        if before_cits != after_cits and _norm(before_text) == _norm(after_text):
            labels.append(EditClass.CITATION_FIX)

        return labels

    def _flash(self, evt: EditEvent) -> tuple[list[EditClass], dict[str, float]]:
        prompt = (
            "Classify the following edit into ONE OR MORE of: "
            "fact_correction, citation_fix, tone, structure, addition, deletion.\n"
            f"Op: {evt.op}\n"
            f"Before: {(evt.before or {}).get('text', '')}\n"
            f"After: {(evt.after or {}).get('text', '')}\n"
            'Return JSON: {"labels": [...], "confidences": {"<label>": <0..1>}}'
        )
        resp = self.flash_client.generate(
            model=self.flash_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        try:
            data = json.loads(resp.text)
        except Exception:
            return [EditClass.TONE], {"tone": 0.5}
        valid = EditClass._value2member_map_
        labels = [EditClass(label) for label in data.get("labels", []) if label in valid]
        if not labels:
            labels = [EditClass.TONE]
        return labels, data.get("confidences", {})
