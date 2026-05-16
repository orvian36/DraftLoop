from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from draftloop_edits.memory import EditMemoryBank
from draftloop_edits.types import EditClass, InducedRule


@pytest.fixture
def bank():
    vec = AsyncMock()
    embedder = MagicMock()
    embedder.embed_documents.return_value = [[0.1] * 1536]
    return EditMemoryBank(vec_index=vec, embedder=embedder)


async def test_upsert_writes_both_collections(bank):
    rule = InducedRule(
        rule_id="rule_x",
        event_id="e1",
        text="rule text",
        trust_weight=1.0,
        pinned=False,
        created_at=datetime.utcnow(),
    )
    await bank.upsert(
        rule=rule,
        edit_classes=[EditClass.FACT_CORRECTION],
        operator_id="op1",
        slot="claims",
        source_evidence_texts=["chunk text"],
    )
    assert bank.vec_index.upsert.await_count == 2


async def test_upsert_rule_only_when_no_evidence(bank):
    rule = InducedRule(
        rule_id="rule_y",
        event_id="e1",
        text="rule",
        trust_weight=1.0,
        pinned=False,
        created_at=datetime.utcnow(),
    )
    await bank.upsert(
        rule=rule,
        edit_classes=[EditClass.TONE],
        operator_id="op1",
        slot="claims",
        source_evidence_texts=[],
    )
    assert bank.vec_index.upsert.await_count == 1
