"""Combine per-page extractor output into a single Markdown blob.

Insert ``<!-- page=N -->`` markers so downstream chunking can preserve page
provenance.
"""

from __future__ import annotations

from draftloop_ingest.engines.base import ExtractedPage


def assemble_markdown(pages: list[ExtractedPage]) -> str:
    parts: list[str] = []
    for p in sorted(pages, key=lambda x: x.page):
        parts.append(f"<!-- page={p.page} -->")
        if p.markdown and p.markdown.strip():
            parts.append(p.markdown.strip())
        else:
            parts.append("\n".join(line.text for line in p.lines))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
