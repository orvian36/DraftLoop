from unittest.mock import MagicMock

from draftloop_drafting.schema import CaseFactSummary, Citation, Fact
from draftloop_edits.critic import CritiqueRunner


def test_critic_returns_per_fact_results():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = (
        '[{"fact_id": "s_1", "supported": true, "violations": [], "suggested_rewrite": null}]'
    )
    fake.generate.return_value = resp
    critic = CritiqueRunner(client=fake, model="gemini-2.5-flash")
    summary = CaseFactSummary(
        parties=[
            Fact(
                sentence_id="s_1",
                text="Acme",
                citations=[Citation(chunk_id="c1", quote="A")],
                confidence="high",
            )
        ],
        jurisdiction=[],
        key_dates=[],
        claims=[],
        relief_sought=[],
        procedural_posture=[],
        key_evidence=[],
    )
    results = critic.review(summary, principles=["Use formal tone"])
    assert results[0].fact_id == "s_1"
    assert results[0].supported


def test_critic_returns_empty_on_invalid_json():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = "not valid json"
    fake.generate.return_value = resp
    critic = CritiqueRunner(client=fake, model="gemini-2.5-flash")
    summary = CaseFactSummary(
        parties=[],
        jurisdiction=[],
        key_dates=[],
        claims=[],
        relief_sought=[],
        procedural_posture=[],
        key_evidence=[],
    )
    assert critic.review(summary, principles=[]) == []
