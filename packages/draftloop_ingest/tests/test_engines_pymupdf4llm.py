from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest.engines.pymupdf4llm_engine import Pdf4llmExtractor


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Complaint")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Plaintiff brings this action against Defendant.")
    c.showPage()
    c.save()


def test_extracts_digital_page_to_markdown(tmp_path):
    pdf = tmp_path / "complaint.pdf"
    _make_digital_pdf(pdf)
    extractor = Pdf4llmExtractor()
    pages = extractor.extract(pdf, page_indices=[0])
    assert len(pages) == 1
    page = pages[0]
    assert page.page == 1
    assert page.class_ == "digital"
    assert "Complaint" in (page.markdown or "")
    assert all(line.engine == "pymupdf4llm" for line in page.lines)
    assert all(line.confidence == 1.0 for line in page.lines)
