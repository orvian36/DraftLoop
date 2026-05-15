import pytest
from pydantic import ValidationError  # noqa: F401  (kept for parity with the plan spec)

from draftloop_core.types import (
    ChunkId,
    DocId,
    MatterId,
    Money,
    NeedsReview,
    RetrievalEngine,
)


def test_id_aliases_are_strings():
    m: MatterId = "M-001"
    d: DocId = "doc_3"
    c: ChunkId = "doc_3_p4_¶12_c_0012"
    assert all(isinstance(x, str) for x in [m, d, c])


def test_needs_review_invariant_low_conf_is_review():
    nr = NeedsReview.from_confidence(0.65)
    assert nr.needs_review is True
    nr = NeedsReview.from_confidence(0.95)
    assert nr.needs_review is False


def test_needs_review_threshold_boundary():
    """Confidence exactly at 0.80 is NOT needs_review."""
    nr = NeedsReview.from_confidence(0.80)
    assert nr.needs_review is False
    nr = NeedsReview.from_confidence(0.7999)
    assert nr.needs_review is True


def test_retrieval_engine_enum():
    assert RetrievalEngine.DENSE.value == "dense"
    assert RetrievalEngine.BM25.value == "bm25"


def test_money_arithmetic_preserves_currency():
    a = Money(amount=1.5, currency="USD")
    b = Money(amount=2.5, currency="USD")
    assert (a + b).amount == 4.0
    assert (a + b).currency == "USD"


def test_money_rejects_mixed_currency():
    a = Money(amount=1.5, currency="USD")
    b = Money(amount=2.5, currency="EUR")
    with pytest.raises(ValueError):
        _ = a + b
