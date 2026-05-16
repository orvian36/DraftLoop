from unittest.mock import MagicMock

from draftloop_edits.replay import ReplayHarness


def test_replay_emits_report_per_week():
    drafter = MagicMock()
    drafter.draft.return_value = MagicMock(summary="reference draft", verification=MagicMock())
    bank = MagicMock()
    exemplars_at = MagicMock(return_value=[])
    harness = ReplayHarness(
        drafter=drafter, memory_bank=bank, exemplars_frozen_at=exemplars_at,
    )
    rep = harness.run(
        matters=[{"matter_id": "M-1", "draft_id": "D-1", "approved_final_draft": "final text"}],
        week_ending="2026-05-15",
    )
    assert rep.matters_replayed == 1
    assert rep.edit_distance_p50 >= 0.0


def test_replay_handles_empty_matters():
    drafter = MagicMock()
    bank = MagicMock()
    harness = ReplayHarness(
        drafter=drafter, memory_bank=bank, exemplars_frozen_at=MagicMock(return_value=[]),
    )
    rep = harness.run(matters=[], week_ending="2026-05-15")
    assert rep.matters_replayed == 0
    assert rep.edit_distance_p50 == 0.0
