"""Digital extractor backed by pymupdf4llm. Returns Markdown + per-line records.

pymupdf4llm's per-chunk metadata may not carry a usable page number in all
versions; we therefore use the position of each chunk in the returned list
(aligned with the ``pages=`` argument we passed in) as the canonical page index.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf4llm

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class Pdf4llmExtractor:
    def extract(self, path: str | Path, page_indices: list[int]) -> list[ExtractedPage]:
        chunks = pymupdf4llm.to_markdown(
            str(path),
            page_chunks=True,
            pages=page_indices,
        )
        out: list[ExtractedPage] = []
        for pos, entry in enumerate(chunks):
            metadata = entry.get("metadata", {}) or {}
            # Prefer pymupdf4llm-supplied page index when present; otherwise fall back
            # to the position-aligned page index from page_indices.
            raw_page = metadata.get("page")
            if isinstance(raw_page, int):
                page_no = raw_page + 1
            elif pos < len(page_indices):
                page_no = page_indices[pos] + 1
            else:
                page_no = pos + 1

            md_text = entry.get("text", "") or ""
            lines = self._lines_from_markdown(md_text, page_no)
            out.append(
                ExtractedPage(
                    page=page_no,
                    width_px=int(metadata.get("page_width", 612) or 612),
                    height_px=int(metadata.get("page_height", 792) or 792),
                    dpi=72,
                    class_="digital",
                    lines=lines,
                    markdown=md_text,
                    engine="pymupdf4llm",
                )
            )
        return out

    @staticmethod
    def _lines_from_markdown(md_text: str, page_no: int) -> list[Line]:
        """One Line per non-empty markdown line.

        Digital text is by definition high-confidence (1.0); bboxes are placeholder
        because pymupdf4llm's per-line coordinates aren't reliably exposed across
        versions. Downstream consumers that need real coordinates would use the
        OCR engines.
        """
        out: list[Line] = []
        for raw in md_text.splitlines():
            text = raw.strip()
            if not text:
                continue
            out.append(
                Line(
                    page=page_no,
                    text=text,
                    bbox=(0, 0, 0, 0),
                    confidence=1.0,
                    engine="pymupdf4llm",
                )
            )
        return out
