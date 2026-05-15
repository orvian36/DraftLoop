"""Digital extractor backed by pymupdf4llm. Returns Markdown + per-line records."""

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
            extract_words=True,
        )
        out: list[ExtractedPage] = []
        for entry in chunks:
            metadata = entry.get("metadata", {}) or {}
            page_no = int(metadata.get("page", 0)) + 1
            md = entry.get("text", "") or ""
            words = entry.get("words", []) or []
            lines = self._group_words(words, page_no)
            out.append(
                ExtractedPage(
                    page=page_no,
                    width_px=int(metadata.get("page_width", 612)),
                    height_px=int(metadata.get("page_height", 792)),
                    dpi=72,
                    class_="digital",
                    lines=lines,
                    markdown=md,
                    engine="pymupdf4llm",
                )
            )
        return out

    @staticmethod
    def _group_words(words: list, page_no: int) -> list[Line]:
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (round(float(w[1]) / 3), float(w[0])))
        grouped: list[list[tuple[float, float, float, float, str]]] = []
        current: list[tuple[float, float, float, float, str]] = []
        current_y: float | None = None
        for w in sorted_words:
            x0, y0, x1, y1, text = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
            if current_y is None or abs(y0 - current_y) <= 3:
                current.append((x0, y0, x1, y1, text))
                current_y = y0
            else:
                grouped.append(current)
                current = [(x0, y0, x1, y1, text)]
                current_y = y0
        if current:
            grouped.append(current)

        lines: list[Line] = []
        for grp in grouped:
            text = " ".join(p[4] for p in grp).strip()
            if not text:
                continue
            xs = [int(p[0]) for p in grp]
            ys = [int(p[1]) for p in grp]
            xes = [int(p[2]) for p in grp]
            yes = [int(p[3]) for p in grp]
            lines.append(
                Line(
                    page=page_no,
                    text=text,
                    bbox=(min(xs), min(ys), max(xes), max(yes)),
                    confidence=1.0,
                    engine="pymupdf4llm",
                )
            )
        return lines
