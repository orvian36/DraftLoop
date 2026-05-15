"""Per-page text-layer probe via pypdfium2.

Determines whether a page has usable embedded text (digital tier)
or must be rasterized + OCR'd (scanned tier).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

TEXT_PRESENCE_MIN_CHARS = 20


@dataclass(frozen=True)
class PageProbe:
    page_index: int
    has_text_layer: bool
    text_char_count: int
    width_px: int
    height_px: int


def probe_pdf(path: str | Path) -> list[PageProbe]:
    path = Path(path)
    probes: list[PageProbe] = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        for i, page in enumerate(pdf):
            try:
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range()
                finally:
                    text_page.close()
            except Exception:
                text = ""
            width = int(page.get_width())
            height = int(page.get_height())
            has_text = len((text or "").strip()) >= TEXT_PRESENCE_MIN_CHARS
            probes.append(
                PageProbe(
                    page_index=i,
                    has_text_layer=has_text,
                    text_char_count=len(text or ""),
                    width_px=width,
                    height_px=height,
                )
            )
    finally:
        pdf.close()
    return probes
