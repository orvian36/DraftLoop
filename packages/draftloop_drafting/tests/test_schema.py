import pytest
from pydantic import ValidationError

from draftloop_drafting.schema import UNSUPPORTED, CaseFactSummary, Citation, Fact


def test_citation_quote_capped_at_240():
    Citation(chunk_id="c1", quote="x" * 240)
    with pytest.raises(ValidationError):
        Citation(chunk_id="c1", quote="x" * 241)


def test_fact_requires_at_least_one_citation_unless_unsupported():
    with pytest.raises(ValidationError):
        Fact(sentence_id="s_1", text="claim", citations=[], confidence="high")
    f = Fact(
        sentence_id="s_1",
        text="claim",
        citations=[Citation(chunk_id="c1", quote="evidence")],
        confidence="high",
    )
    assert f.citations[0].chunk_id == "c1"


def test_unsupported_sentinel_allows_empty_citations():
    f = Fact(sentence_id="s_1", text=UNSUPPORTED, citations=[], confidence="low")
    assert f.text == "UNSUPPORTED"


def test_case_fact_summary_holds_all_slots():
    f = Fact(
        sentence_id="s_1",
        text="x",
        citations=[Citation(chunk_id="c1", quote="y")],
        confidence="high",
    )
    summary = CaseFactSummary(
        parties=[f],
        jurisdiction=[f],
        key_dates=[f],
        claims=[f],
        relief_sought=[f],
        procedural_posture=[f],
        key_evidence=[f],
    )
    assert len(summary.parties) == 1
