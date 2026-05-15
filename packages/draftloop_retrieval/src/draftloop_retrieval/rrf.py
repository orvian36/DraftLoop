"""Reciprocal Rank Fusion (k=60 default)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusedHit:
    id: str
    score: float
    engines: tuple[str, ...]


def rrf_fuse(
    rankings: list[list[tuple[str, float]]],
    *,
    k: int = 60,
    top_k: int = 50,
    engine_names: list[str] | None = None,
) -> list[FusedHit]:
    if engine_names is None:
        engine_names = [f"engine_{i}" for i in range(len(rankings))]
    scores: dict[str, float] = {}
    engines: dict[str, set[str]] = {}
    for engine_idx, ranking in enumerate(rankings):
        for rank, (doc_id, _score) in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            engines.setdefault(doc_id, set()).add(engine_names[engine_idx])
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [FusedHit(id=i, score=s, engines=tuple(sorted(engines[i]))) for i, s in ordered]
