"""Structure-aware Markdown splitter.

Tier 1: split on H1/H2/H3 headings.
Tier 2: within each section, recursive ~512-token chunking with overlap.

Every emitted Chunk carries (char_start, char_end) into the source Markdown
and a stable chunk_id derived from (doc_id, ingest_version, char_start, char_end).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from typing import Any

import tiktoken

from draftloop_retrieval.types import Chunk

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_PAGE_MARKER_RE = re.compile(r"<!--\s*page=(\d+)\s*-->")


class StructuralSplitter:
    def __init__(self, chunk_size_tokens: int = 512, overlap_tokens: int = 64) -> None:
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")

    def split(
        self,
        *,
        markdown: str,
        doc_id: str,
        matter_id: str,
        ingest_version: str,
    ) -> Iterator[Chunk]:
        sections = self._split_sections(markdown)
        for section in sections:
            yield from self._recursive_split(
                section_text=section["text"],
                section_start=section["start"],
                section_label=section["label"],
                full_markdown=markdown,
                doc_id=doc_id,
                matter_id=matter_id,
                ingest_version=ingest_version,
            )

    def _split_sections(self, md: str) -> list[dict[str, Any]]:
        headings = [(m.start(), m.group(2).strip()) for m in _HEADING_RE.finditer(md)]
        sections: list[dict[str, Any]] = []
        if not headings:
            sections.append({"start": 0, "label": None, "text": md})
            return sections
        if headings[0][0] > 0:
            sections.append({"start": 0, "label": None, "text": md[: headings[0][0]]})
        for i, (pos, label) in enumerate(headings):
            end = headings[i + 1][0] if i + 1 < len(headings) else len(md)
            sections.append({"start": pos, "label": label, "text": md[pos:end]})
        return sections

    def _page_for_offset(self, full_md: str, offset: int) -> int:
        page = 1
        for m in _PAGE_MARKER_RE.finditer(full_md, 0, offset + 1):
            page = int(m.group(1))
        return page

    def _recursive_split(
        self,
        *,
        section_text: str,
        section_start: int,
        section_label: str | None,
        full_markdown: str,
        doc_id: str,
        matter_id: str,
        ingest_version: str,
    ) -> Iterator[Chunk]:
        tokens = self._enc.encode(section_text)
        if not tokens:
            return
        step = max(1, self.chunk_size_tokens - self.overlap_tokens)
        for start_tok in range(0, len(tokens), step):
            window = tokens[start_tok : start_tok + self.chunk_size_tokens]
            if not window:
                continue
            slice_text = self._enc.decode(window)
            anchor = slice_text.strip()[:40]
            local_start = section_text.find(anchor) if anchor else 0
            if local_start < 0:
                local_start = 0
            char_start = section_start + local_start
            char_end = char_start + len(slice_text)
            if char_end > len(full_markdown):
                char_end = len(full_markdown)
            actual_text = full_markdown[char_start:char_end]
            page = self._page_for_offset(full_markdown, char_start)
            chunk_id = self._chunk_id(doc_id, ingest_version, char_start, char_end)
            yield Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                matter_id=matter_id,
                page=page,
                section_label=section_label,
                para_id=None,
                char_start=char_start,
                char_end=char_end,
                text=actual_text.strip(),
                context_prefix="",
                embedding_text=actual_text.strip(),
                embedding_dim=1536,
                confidence_min=1.0,
                contains_needs_review=False,
                ingest_version=ingest_version,
            )
            if start_tok + self.chunk_size_tokens >= len(tokens):
                break

    @staticmethod
    def _chunk_id(doc_id: str, version: str, start: int, end: int) -> str:
        h = hashlib.sha1(f"{doc_id}|{version}|{start}|{end}".encode()).hexdigest()[:10]
        return f"{doc_id}_c_{h}"
