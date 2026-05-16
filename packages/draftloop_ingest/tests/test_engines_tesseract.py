import shutil
from io import BytesIO

import pytest
from draftloop_ingest.engines.tesseract_engine import TesseractEngine
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract binary not installed; skipping",
)


def _render_text_image(text: str) -> bytes:
    img = Image.new("L", (800, 200), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill=0, font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_tesseract_reads_obvious_text():
    image_bytes = _render_text_image("Plaintiff brings this action.")
    engine = TesseractEngine()
    result = engine.ocr(
        image_bytes=image_bytes,
        page=1,
        width_px=800,
        height_px=200,
        dpi=300,
    )
    joined = " ".join(line.text for line in result.lines)
    assert "Plaintiff" in joined
    assert all(line.engine == "tesseract" for line in result.lines)
    assert all(0.0 <= line.confidence <= 1.0 for line in result.lines)
