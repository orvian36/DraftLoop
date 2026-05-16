"""Dual-vector edit memory bank backed by two Chroma collections."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_core.storage import VectorIndex, VectorItem
from draftloop_retrieval.embedder import GeminiEmbedder

from draftloop_edits.types import EditClass, InducedRule

RULE_COLLECTION = "edit_memory_rule"
EVIDENCE_COLLECTION = "edit_memory_evidence"


@dataclass
class EditMemoryBank:
    vec_index: VectorIndex
    embedder: GeminiEmbedder

    async def upsert(
        self,
        *,
        rule: InducedRule,
        edit_classes: list[EditClass],
        operator_id: str,
        slot: str,
        source_evidence_texts: list[str],
    ) -> None:
        rule_vec = self.embedder.embed_documents([rule.text])[0]
        await self.vec_index.upsert(
            RULE_COLLECTION,
            [
                VectorItem(
                    id=rule.rule_id,
                    vector=rule_vec,
                    metadata={
                        "rule_id": rule.rule_id,
                        "event_id": rule.event_id,
                        "edit_classes": ",".join(c.value for c in edit_classes),
                        "operator_id": operator_id,
                        "slot": slot,
                        "trust_weight": rule.trust_weight,
                        "pinned": rule.pinned,
                        "created_at": rule.created_at.isoformat(),
                    },
                    document=rule.text,
                )
            ],
        )
        if source_evidence_texts:
            evi_text = "\n".join(source_evidence_texts)
            evi_vec = self.embedder.embed_documents([evi_text])[0]
            await self.vec_index.upsert(
                EVIDENCE_COLLECTION,
                [
                    VectorItem(
                        id=rule.rule_id,
                        vector=evi_vec,
                        metadata={
                            "rule_id": rule.rule_id,
                            "operator_id": operator_id,
                            "slot": slot,
                            "trust_weight": rule.trust_weight,
                        },
                        document=evi_text,
                    )
                ],
            )
