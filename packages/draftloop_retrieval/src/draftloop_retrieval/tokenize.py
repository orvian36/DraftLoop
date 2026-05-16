"""BM25 pre-tokenizer that preserves legal citations as single tokens."""

from __future__ import annotations

import re

_STATUTE_RE = re.compile(r"\d{1,3}\s+U\.?S\.?C\.?\s*§\s*\d+(?:\(\w+\))?")
_REPORTER_RE = re.compile(r"\d+\s+U\.?S\.?\s+\d+")


def tokenize_for_bm25(text: str) -> list[str]:
    preserved: list[str] = []
    placeholders: dict[str, str] = {}

    def stash(m: re.Match[str]) -> str:
        token = m.group(0).strip()
        placeholder = f"__CIT{len(preserved)}__"
        preserved.append(token)
        placeholders[placeholder] = token
        return placeholder

    cleaned = _STATUTE_RE.sub(stash, text)
    cleaned = _REPORTER_RE.sub(stash, cleaned)
    cleaned = re.sub(r"[^\w§_]+", " ", cleaned, flags=re.UNICODE)

    tokens: list[str] = []
    for tok in cleaned.split():
        if tok in placeholders:
            tokens.append(placeholders[tok])
        else:
            tokens.append(tok.lower())
    return tokens
