from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest.probe import PageProbe, probe_pdf


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, "Hello DraftLoop. This is a digital-native PDF.")
    c.showPage()
    c.drawString(72, 720, "Second page also has text.")
    c.showPage()
    c.save()


def test_probe_detects_text_pages(tmp_path):
    pdf = tmp_path / "digital.pdf"
    _make_digital_pdf(pdf)
    probes = probe_pdf(pdf)
    assert len(probes) == 2
    assert all(p.has_text_layer for p in probes)
    assert probes[0].text_char_count >= 30
    assert probes[0].width_px > 0 and probes[0].height_px > 0
    assert isinstance(probes[0], PageProbe)


def test_probe_marks_empty_page_as_scan_candidate(tmp_path):
    pdf = tmp_path / "scan.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.rect(100, 100, 200, 200, fill=1)
    c.showPage()
    c.save()
    probes = probe_pdf(pdf)
    assert len(probes) == 1
    assert probes[0].has_text_layer is False
