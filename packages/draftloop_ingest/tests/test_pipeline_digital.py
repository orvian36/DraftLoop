from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest import IngestPipeline, IngestRequest


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Complaint")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Plaintiff brings this action against Defendant for breach of contract.")
    c.showPage()
    c.drawString(72, 720, "Page 2: Procedural posture is the motion to dismiss stage.")
    c.showPage()
    c.save()


def test_pipeline_digital_path(tmp_path):
    pdf = tmp_path / "complaint.pdf"
    _make_digital_pdf(pdf)
    pipeline = IngestPipeline()
    result = pipeline.run(IngestRequest(matter_id="M-001", source_path=str(pdf)))
    assert result.failed is False
    assert len(result.pages) == 2
    assert all(p.class_ == "digital" for p in result.pages)
    assert "Complaint" in result.markdown
    assert "<!-- page=1 -->" in result.markdown
    assert "<!-- page=2 -->" in result.markdown
    assert result.aggregate_confidence == 1.0
    assert result.engines_used == {1: ["pymupdf4llm"], 2: ["pymupdf4llm"]}
