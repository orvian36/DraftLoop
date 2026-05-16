"""Nightly cluster of induced rules into Constitutional Principles.

HDBSCAN is an optional dependency. If unavailable, ``cluster()`` returns ``[]``
and the catalog operates in a degraded mode (drafting still proceeds without
auto-clustered principles).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from draftloop_core.llm import GeminiClient
from draftloop_retrieval.embedder import GeminiEmbedder

from draftloop_edits.types import InducedRule, Principle

PROMPT = """The following operator-edit rules likely express the same underlying preference.
Synthesize them into ONE principle (≤30 words, imperative voice). Return only the principle text.

Rules:
{rules}
"""


@dataclass
class RuleCatalog:
    embedder: GeminiEmbedder
    flash_client: GeminiClient
    flash_model: str
    min_cluster_size: int = 3

    def cluster(self, rules: list[InducedRule]) -> list[Principle]:
        if len(rules) < self.min_cluster_size:
            return []
        try:
            import hdbscan  # type: ignore[import-not-found]
        except Exception:
            return []

        vectors = np.array(self.embedder.embed_documents([r.text for r in rules]))
        if vectors.shape[0] == 0:
            return []
        clusterer = hdbscan.HDBSCAN(min_cluster_size=self.min_cluster_size, metric="euclidean")
        labels = clusterer.fit_predict(vectors)
        principles: list[Principle] = []
        for label in set(labels):
            if label == -1:
                continue
            idxs = [i for i, lbl in enumerate(labels) if lbl == label]
            members = [rules[i] for i in idxs]
            text = self._summarize(members)
            pid = "principle_" + hashlib.sha1(text.encode()).hexdigest()[:10]
            principles.append(
                Principle(
                    principle_id=pid,
                    text=text,
                    source_rule_ids=[r.rule_id for r in members],
                    status="proposed",
                    coverage_count=len(members),
                    approved_at=None,
                    approved_by=None,
                )
            )
        return principles

    def _summarize(self, rules: list[InducedRule]) -> str:
        prompt = PROMPT.format(rules="\n".join(f"- {r.text}" for r in rules))
        resp = self.flash_client.generate(model=self.flash_model, contents=prompt)
        return (resp.text or "").strip() or rules[0].text
