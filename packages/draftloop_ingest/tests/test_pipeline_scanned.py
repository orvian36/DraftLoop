import importlib.util
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest import IngestPipeline, IngestRequest

paddleocr_available = importlib.util.find_spec("paddleocr") is not None
tesseract_available = shutil.which("tesseract") is not None

pytestmark = pytest.mark.skipif(
    not (paddleocr_available or tesseract_available),
    reason="neither paddleocr nor tesseract available; scan path cannot run",
)


def _make_scanned_pdf(path) -> None:
    img = Image.new("L", (1700, 2200), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    draw.text((150, 300), "Notice of Hearing", fill=0, font=font)
    draw.text((150, 420), "Hearing scheduled for 2026-06-15.", fill=0, font=font)
    img_path = str(path) + ".png"
    img.save(img_path)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawImage(img_path, 0, 0, width=letter[0], height=letter[1])
    c.showPage()
    c.save()


def test_pipeline_scan_path(tmp_path):
    pdf = tmp_path / "notice.pdf"
    _make_scanned_pdf(pdf)
    pipeline = IngestPipeline()
    result = pipeline.run(IngestRequest(matter_id="M-001", source_path=str(pdf)))
    assert result.failed is False
    assert len(result.pages) == 1
    text = " ".join(line.text for line in result.pages[0].lines)
    assert "Notice" in text or "Hearing" in text or "2026" in text
