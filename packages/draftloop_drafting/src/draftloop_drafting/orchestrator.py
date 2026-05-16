"""Drafter — orchestrates assembly -> generate -> verify -> audit."""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from dataclasses import dataclass

from draftloop_drafting.audit_trail import AuditTrailWriter
from draftloop_drafting.generator import Generator
from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_drafting.schema import UNSUPPORTED, CaseFactSummary, Fact
from draftloop_drafting.types import (
    DraftRequest,
    DraftResult,
    FactVerification,
    VerificationReport,
)
from draftloop_drafting.verifier import Verifier


@dataclass
class Drafter:
    prompt_assembler: PromptAssembler
    generator: Generator
    verifier: Verifier
    audit_writer: AuditTrailWriter

    def draft(self, req: DraftRequest) -> DraftResult:
        start = time.monotonic()
        system, user = self.prompt_assembler.render(
            matter_id=req.matter_id,
            retrieval_hits=req.retrieval_hits,
            fact_exemplars=req.exemplars.get("fact", []),
            style_exemplars=req.exemplars.get("style", []),
            principles=req.principles,
        )
        prompt_hash = hashlib.sha256((system + user).encode()).hexdigest()

        summary, usage = self.generator.generate(system_prompt=system, user_prompt=user)

        chunks_by_id = {
            hit.chunk.chunk_id: hit.chunk.text
            for hits in req.retrieval_hits.values()
            for hit in hits
        }

        verified, fact_verifs = self._verify_all(summary, chunks_by_id)
        summary_counts = Counter(fv.final_verdict for fv in fact_verifs)

        verification_report = VerificationReport(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            fact_results=fact_verifs,
            summary={k: int(v) for k, v in summary_counts.items()},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

        retrieved_chunks_meta = [
            {
                "chunk_id": hit.chunk.chunk_id,
                "slot": slot,
                "rerank_score": hit.rerank_score,
                "engines": list(hit.retrieval_engines),
            }
            for slot, hits in req.retrieval_hits.items()
            for hit in hits
        ]
        audit_path = self.audit_writer.write(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            model=req.drafter_model,
            drafter_mode=req.drafter_mode,
            prompt_hash=prompt_hash,
            cache_name=None,
            retrieved_chunks=retrieved_chunks_meta,
            exemplars_used=req.exemplars.get("fact", []) + req.exemplars.get("style", []),
            style_rules_active=req.principles,
            verification={"summary": dict(summary_counts)},
            token_usage={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cached": usage.cached_tokens,
            },
            cost_usd=0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
            ingest_versions={},
        )

        return DraftResult(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            summary=verified,
            verification=verification_report,
            audit_trail_path=audit_path,
            cost_usd=0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
            token_usage={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cached": usage.cached_tokens,
            },
        )

    def _verify_all(
        self, summary: CaseFactSummary, chunks_by_id: dict[str, str]
    ) -> tuple[CaseFactSummary, list[FactVerification]]:
        results: list[FactVerification] = []
        new_slots: dict[str, list[Fact]] = {}
        for slot_name, facts in summary.model_dump().items():
            new_facts: list[Fact] = []
            for fact_dict in facts:
                fact = Fact.model_validate(fact_dict)
                fv = self.verifier.verify_fact(fact, chunks_by_id)
                results.append(fv)
                if fv.final_verdict == "rewrite_to_unsupported":
                    new_facts.append(
                        Fact(
                            sentence_id=fact.sentence_id,
                            text=UNSUPPORTED,
                            citations=[],
                            confidence="low",
                        )
                    )
                else:
                    new_facts.append(fact)
            new_slots[slot_name] = new_facts
        verified = CaseFactSummary.model_validate(new_slots)
        return verified, results
