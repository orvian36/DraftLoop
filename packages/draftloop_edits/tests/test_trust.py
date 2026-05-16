from datetime import datetime

from draftloop_edits.trust import ReversionEvent, TrustEngine


def test_reversion_demotes_originator():
    engine = TrustEngine()
    engine.record_edit(
        operator_id="op_A", sentence_id="s_1", text="ISO date", ts=datetime(2026, 1, 1)
    )
    engine.record_reversion(
        ReversionEvent(reverter="op_B", original_op="op_A", sentence_id="s_1", days_after=3)
    )
    score = engine.score("op_A")
    assert score.current_weight < 1.0
    assert score.reversions_against == 1


def test_pinned_edit_keeps_weight_one():
    engine = TrustEngine()
    engine.record_edit("op_A", "s_1", "ISO date", datetime.utcnow(), pinned=True)
    engine.record_reversion(
        ReversionEvent(reverter="op_B", original_op="op_A", sentence_id="s_1", days_after=3)
    )
    score = engine.score("op_A")
    assert score.current_weight == 1.0


def test_late_reversion_ignored():
    engine = TrustEngine()
    engine.record_edit("op_A", "s_1", "ISO date", datetime.utcnow())
    engine.record_reversion(
        ReversionEvent(reverter="op_B", original_op="op_A", sentence_id="s_1", days_after=30)
    )
    score = engine.score("op_A")
    assert score.current_weight == 1.0


def test_anti_poisoning_after_repeated_reversions():
    engine = TrustEngine()
    engine.record_edit("noisy_op", "s_1", "bad edit", datetime.utcnow())
    engine.record_edit("noisy_op", "s_2", "bad edit", datetime.utcnow())
    engine.record_edit("noisy_op", "s_3", "bad edit", datetime.utcnow())
    for sid in ("s_1", "s_2", "s_3"):
        engine.record_reversion(
            ReversionEvent(
                reverter="good_op", original_op="noisy_op", sentence_id=sid, days_after=2
            )
        )
    score = engine.score("noisy_op")
    assert score.current_weight < 0.5
