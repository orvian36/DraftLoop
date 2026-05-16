from datetime import datetime
from unittest.mock import MagicMock

from draftloop_edits.rule_inducer import RuleInducer
from draftloop_edits.types import ClassifiedEdit, EditClass, EditEvent


def test_rule_induced_with_flash():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = "Use ISO-8601 dates instead of long-form prose dates."
    fake.generate.return_value = resp
    inducer = RuleInducer(client=fake, model="gemini-2.5-flash")
    evt = EditEvent(
        event_id="e1",
        draft_id="D",
        matter_id="M",
        slot="claims",
        sentence_id="s",
        op="fact_text_changed",
        before={"text": "filed on March 14, 2024."},
        after={"text": "filed on 2024-03-14."},
        source_evidence_ids=[],
        word_diff=None,
        time_to_edit_ms=0,
        operator_id="op1",
        draft_model_version="v1",
        prompt_hash="h",
        timestamp=datetime.utcnow().isoformat(),
    )
    cls = ClassifiedEdit(
        event_id="e1",
        edit_class_labels=[EditClass.FACT_CORRECTION, EditClass.TONE],
        classifier_confidences={},
        classifier_version="v1",
        classified_at=datetime.utcnow(),
    )
    rule = inducer.induce(evt, cls)
    assert rule is not None
    assert "ISO-8601" in rule.text


def test_no_rule_for_pure_addition():
    inducer = RuleInducer(client=MagicMock(), model="gemini-2.5-flash")
    evt = EditEvent(
        event_id="e1",
        draft_id="D",
        matter_id="M",
        slot="claims",
        sentence_id="s",
        op="fact_added",
        before=None,
        after={"text": "new"},
        source_evidence_ids=[],
        word_diff=None,
        time_to_edit_ms=0,
        operator_id="op1",
        draft_model_version="v1",
        prompt_hash="h",
        timestamp=datetime.utcnow().isoformat(),
    )
    cls = ClassifiedEdit(
        event_id="e1",
        edit_class_labels=[EditClass.ADDITION],
        classifier_confidences={},
        classifier_version="v1",
        classified_at=datetime.utcnow(),
    )
    assert inducer.induce(evt, cls) is None
