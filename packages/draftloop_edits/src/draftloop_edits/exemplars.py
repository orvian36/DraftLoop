"""ExemplarRetriever — fact-pass + style-pass, RRF, trust + recency weighting, token budget."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from draftloop_core.storage import VectorIndex
from draftloop_retrieval.embedder import GeminiEmbedder
from draftloop_retrieval.rrf import rrf_fuse

from draftloop_edits.memory import EVIDENCE_COLLECTION, RULE_COLLECTION
from draftloop_edits.types import EditClass, Exemplar, ExemplarBundle

FACT_CLASSES = {EditClass.FACT_CORRECTION, EditClass.CITATION_FIX}
STYLE_CLASSES = {EditClass.TONE, EditClass.STRUCTURE}


def _approx_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


@dataclass
class ExemplarRetriever:
    vec_index: VectorIndex
    embedder: GeminiEmbedder
    max_fact: int = 5
    max_style: int = 3
    token_budget: int = 2000
    per_operator_cap: int = 2

    async def recall(
        self,
        *,
        slot: str,
        source_evidence_texts: list[str],
        rule_intent: str,
    ) -> ExemplarBundle:
        if not source_evidence_texts:
            return ExemplarBundle(fact_exemplars=[], style_exemplars=[], total_tokens=0)
        evi_vec = self.embedder.embed_documents(["\n".join(source_evidence_texts)])[0]
        rule_vec = self.embedder.embed_queries([rule_intent])[0]

        evi_hits = await self.vec_index.search(EVIDENCE_COLLECTION, evi_vec, top_k=20)
        rule_hits = await self.vec_index.search(RULE_COLLECTION, rule_vec, top_k=20)

        fused = rrf_fuse(
            [
                [(h.id, h.score) for h in evi_hits],
                [(h.id, h.score) for h in rule_hits],
            ],
            k=60,
            top_k=20,
        )
        all_hits = {h.id: h for h in evi_hits + rule_hits}

        scored: list[tuple[Exemplar, float]] = []
        for f in fused:
            hit = all_hits.get(f.id)
            if hit is None:
                continue
            md = hit.metadata
            classes = [EditClass(c) for c in (md.get("edit_classes", "") or "").split(",") if c]
            created = _parse_dt(md.get("created_at", ""))
            age_days = max(0, (datetime.utcnow() - created).days)
            base = f.score * float(md.get("trust_weight", 1.0)) * math.exp(-age_days / 30.0)
            exemplar = Exemplar(
                edit_id=md.get("event_id", md.get("rule_id", "?")),
                induced_rule=hit.document or "",
                before_text=None,
                after_text=None,
                edit_class=classes,
                operator_id=md.get("operator_id", "?"),
                trust_weight=float(md.get("trust_weight", 1.0)),
                age_days=age_days,
            )
            scored.append((exemplar, base))

        scored.sort(key=lambda p: p[1], reverse=True)
        fact_pass = self._select(scored, FACT_CLASSES, self.max_fact)
        style_pass = self._select(scored, STYLE_CLASSES, self.max_style)
        total = sum(_approx_tokens(e.induced_rule) for e in fact_pass + style_pass)
        while total > self.token_budget and (fact_pass or style_pass):
            if style_pass:
                style_pass.pop()
            else:
                fact_pass.pop()
            total = sum(_approx_tokens(e.induced_rule) for e in fact_pass + style_pass)
        return ExemplarBundle(
            fact_exemplars=fact_pass, style_exemplars=style_pass, total_tokens=total
        )

    def _select(
        self,
        scored: list[tuple[Exemplar, float]],
        allowed: set[EditClass],
        cap: int,
    ) -> list[Exemplar]:
        chosen: list[Exemplar] = []
        per_op: dict[str, int] = {}
        for ex, _ in scored:
            if not allowed.intersection(ex.edit_class):
                continue
            if per_op.get(ex.operator_id, 0) >= self.per_operator_cap:
                continue
            chosen.append(ex)
            per_op[ex.operator_id] = per_op.get(ex.operator_id, 0) + 1
            if len(chosen) >= cap:
                break
        return chosen
