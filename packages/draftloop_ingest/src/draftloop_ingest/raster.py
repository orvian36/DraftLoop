"""Rasterize PDF pages to PNG bytes at a target DPI."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium


def rasterize_page(path: str | Path, page_index: int, dpi: int = 300) -> bytes:
    """Return PNG bytes for one page at the requested DPI."""
    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[page_index]
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        buf = BytesIO()
        pil.save(buf, format="PNG")
        return buf.getvalue()
    finally:
        pdf.close()
