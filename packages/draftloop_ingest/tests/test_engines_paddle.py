import importlib.util
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont

paddleocr_available = importlib.util.find_spec("paddleocr") is not None

pytestmark = pytest.mark.skipif(
    not paddleocr_available,
    reason="paddleocr not installed; skipping",
)


def _render_text_image(text: str) -> bytes:
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill="black", font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_paddle_reads_printed_text():
    from draftloop_ingest.engines.paddle_engine import PaddleEngine

    image_bytes = _render_text_image("Motion to Dismiss filed.")
    engine = PaddleEngine()
    result = engine.ocr(
        image_bytes=image_bytes,
        page=1,
        width_px=800,
        height_px=200,
        dpi=300,
    )
    joined = " ".join(line.text for line in result.lines)
    assert "Motion" in joined or "Dismiss" in joined
    assert all(line.engine == "paddleocr" for line in result.lines)
