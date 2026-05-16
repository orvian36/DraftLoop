from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.markdown_assembler import assemble_markdown
from draftloop_ingest.types import Line


def _line(page: int, text: str, conf: float = 1.0, y: int = 100) -> Line:
    return Line(
        page=page,
        text=text,
        bbox=(0, y, 100, y + 20),
        confidence=conf,
        engine="pymupdf4llm",
    )


def test_assemble_markdown_emits_per_page_marker():
    p1 = ExtractedPage(
        page=1,
        width_px=612,
        height_px=792,
        dpi=72,
        class_="digital",
        lines=[_line(1, "Heading", 1.0), _line(1, "body text", 1.0, y=150)],
        markdown="# Heading\n\nbody text",
        engine="pymupdf4llm",
    )
    p2 = ExtractedPage(
        page=2,
        width_px=612,
        height_px=792,
        dpi=72,
        class_="digital",
        lines=[_line(2, "Second page", 1.0)],
        markdown="Second page content here.",
        engine="pymupdf4llm",
    )
    md = assemble_markdown([p1, p2])
    assert "<!-- page=1 -->" in md
    assert "<!-- page=2 -->" in md
    assert md.index("<!-- page=1 -->") < md.index("<!-- page=2 -->")
    assert "Heading" in md
    assert "Second page" in md


def test_assemble_markdown_falls_back_when_engine_returned_no_md():
    p = ExtractedPage(
        page=1,
        width_px=612,
        height_px=792,
        dpi=72,
        class_="clean_scan",
        lines=[_line(1, "first line"), _line(1, "second line", y=130)],
        markdown="",
        engine="paddleocr",
    )
    md = assemble_markdown([p])
    assert "first line" in md
    assert "second line" in md
