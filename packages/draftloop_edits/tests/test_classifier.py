from datetime import datetime
from unittest.mock import MagicMock

from draftloop_edits.classifier import EditClassifier
from draftloop_edits.types import EditClass, EditEvent


def _evt(op: str, before_text: str = "", after_text: str = "", before_cits=None, after_cits=None) -> EditEvent:
    return EditEvent(
        event_id="e", draft_id="D", matter_id="M", slot="claims",
        sentence_id="s", op=op,
        before={"text": before_text, "citations": before_cits or []},
        after={"text": after_text, "citations": after_cits or []},
        source_evidence_ids=[],
        word_diff=None, time_to_edit_ms=0,
        operator_id="op", draft_model_version="v", prompt_hash="h",
        timestamp=datetime.utcnow().isoformat(),
    )


def test_date_change_is_fact_correction():
    c = EditClassifier(flash_client=MagicMock(), flash_model="gemini-2.5-flash")
    res = c.classify(_evt("fact_text_changed",
                          before_text="filed on March 14, 2024.",
                          after_text="filed on 2024-03-14."))
    assert EditClass.FACT_CORRECTION in res.edit_class_labels


def test_only_citation_diff_is_citation_fix():
    c = EditClassifier(flash_client=MagicMock(), flash_model="gemini-2.5-flash")
    res = c.classify(_evt("citation_added",
                          before_text="claim", after_text="claim",
                          before_cits=[{"chunk_id": "c1", "quote": "x"}],
                          after_cits=[{"chunk_id": "c2", "quote": "x"}]))
    assert EditClass.CITATION_FIX in res.edit_class_labels


def test_whitespace_only_is_tone():
    c = EditClassifier(flash_client=MagicMock(), flash_model="gemini-2.5-flash")
    res = c.classify(_evt("fact_text_changed",
                          before_text="Plaintiff brings claim.",
                          after_text="Plaintiff brings  claim. "))
    assert EditClass.TONE in res.edit_class_labels


def test_addition_op_is_addition():
    c = EditClassifier(flash_client=MagicMock(), flash_model="gemini-2.5-flash")
    res = c.classify(_evt("fact_added", before_text="", after_text="new"))
    assert EditClass.ADDITION in res.edit_class_labels


def test_falls_back_to_flash_when_ambiguous():
    flash = MagicMock()
    resp = MagicMock()
    resp.text = '{"labels": ["tone"], "confidences": {"tone": 0.9}}'
    flash.generate.return_value = resp
    c = EditClassifier(flash_client=flash, flash_model="gemini-2.5-flash")
    res = c.classify(_evt("fact_text_changed",
                          before_text="Plaintiff alleges breach.",
                          after_text="The plaintiff has alleged a breach."))
    assert EditClass.TONE in res.edit_class_labels
