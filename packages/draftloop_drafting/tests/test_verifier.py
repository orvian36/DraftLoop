from unittest.mock import MagicMock

from draftloop_drafting.schema import Citation, Fact
from draftloop_drafting.verifier import Verifier


def _hhem(score):
    m = MagicMock()
    m.score.return_value = score
    return m


def test_verifier_passes_when_substring_and_hhem_high():
    fake_judge = MagicMock()
    verifier = Verifier(hhem=_hhem(0.95), judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Plaintiff alleges breach.",
        citations=[Citation(chunk_id="c1", quote="Plaintiff alleges breach")],
        confidence="high",
    )
    chunks = {"c1": "On 2024-03-14, Plaintiff alleges breach of the SaaS agreement."}
    fv = verifier.verify_fact(fact, chunks)
    assert fv.final_verdict == "pass"
    fake_judge.generate.assert_not_called()


def test_verifier_rewrites_when_substring_misses():
    verifier = Verifier(hhem=_hhem(0.9), judge=MagicMock(), judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Plaintiff was on Mars.",
        citations=[Citation(chunk_id="c1", quote="Plaintiff was on Mars")],
        confidence="high",
    )
    chunks = {"c1": "Plaintiff alleges breach."}
    fv = verifier.verify_fact(fact, chunks)
    assert fv.substring_passed is False
    assert fv.final_verdict == "rewrite_to_unsupported"


def test_verifier_escalates_uncertain_to_judge():
    fake_judge = MagicMock()
    judge_resp = MagicMock()
    judge_resp.text = "SUPPORTED"
    fake_judge.generate.return_value = judge_resp
    verifier = Verifier(hhem=_hhem(0.6), judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Allegation",
        citations=[Citation(chunk_id="c1", quote="alleg")],
        confidence="high",
    )
    fv = verifier.verify_fact(fact, {"c1": "alleg"})
    assert fv.llm_judge == "supported"
    assert fv.final_verdict == "pass"


def test_verifier_falls_through_to_judge_when_hhem_unavailable():
    fake_judge = MagicMock()
    judge_resp = MagicMock()
    judge_resp.text = "UNSUPPORTED"
    fake_judge.generate.return_value = judge_resp
    verifier = Verifier(hhem=_hhem(None), judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Allegation",
        citations=[Citation(chunk_id="c1", quote="alleg")],
        confidence="high",
    )
    fv = verifier.verify_fact(fact, {"c1": "alleg"})
    assert fv.final_verdict == "rewrite_to_unsupported"
