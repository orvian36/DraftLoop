import pytest

from draftloop_ingest.types import (
    DocStatus,
    IngestRequest,
    IngestResult,
    Line,
    NeedsReviewSpan,
    Page,
)


def test_line_invariant_low_conf_is_review():
    line = Line(
        page=1,
        text="hello",
        bbox=(0, 0, 10, 10),
        confidence=0.7,
        engine="paddleocr",
    )
    assert line.needs_review is True


def test_line_invariant_high_conf_is_not_review():
    line = Line(
        page=1,
        text="hello",
        bbox=(0, 0, 10, 10),
        confidence=0.95,
        engine="paddleocr",
    )
    assert line.needs_review is False


def test_doc_status_transitions_are_well_defined():
    assert DocStatus.UPLOADED.value == "uploaded"
    assert DocStatus.READY.value == "ready"
    assert DocStatus.FAILED.value == "failed"


def test_ingest_request_requires_source_path():
    with pytest.raises(Exception):
        IngestRequest()
    req = IngestRequest(matter_id="M-001", source_path="/tmp/x.pdf")
    assert req.matter_id == "M-001"


def test_ingest_result_aggregate_confidence_validates():
    page = Page(
        page=1,
        width_px=816,
        height_px=1056,
        dpi=96,
        class_="digital",
        engines_used=["pymupdf4llm"],
        lines=[],
        needs_review=False,
    )
    res = IngestResult(
        doc_id="doc_1",
        source_path="/tmp/x.pdf",
        pages=[page],
        markdown="<!-- page=1 -->",
        needs_review_spans=[],
        aggregate_confidence=0.99,
        engines_used={1: ["pymupdf4llm"]},
        duration_ms=120,
        ingest_version="v1",
    )
    assert res.doc_id == "doc_1"
    assert res.pages[0].class_ == "digital"


def test_needs_review_span_carries_reason():
    span = NeedsReviewSpan(
        page=2,
        bbox=(1, 2, 3, 4),
        text="illegible",
        confidence=0.3,
        reason="illegible",
    )
    assert span.reason == "illegible"
