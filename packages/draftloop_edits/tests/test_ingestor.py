from datetime import datetime

import pytest

from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore
from draftloop_edits.ingestor import EditIngestor
from draftloop_edits.types import EditEvent


@pytest.fixture
async def store(tmp_path):
    s = SqliteDocumentStore(tmp_path / "edits.db")
    await s.init_schema()
    return s


def _event(eid: str) -> EditEvent:
    return EditEvent(
        event_id=eid,
        draft_id="D-1",
        matter_id="M-1",
        slot="claims",
        sentence_id="s_1",
        op="fact_text_changed",
        before={"text": "x"},
        after={"text": "y"},
        source_evidence_ids=["c1"],
        word_diff="@@-x+y@@",
        time_to_edit_ms=5000,
        operator_id="op1",
        draft_model_version="v1",
        prompt_hash="h",
        timestamp=datetime.utcnow().isoformat(),
    )


async def test_ingest_persists_events(store):
    ing = EditIngestor(store=store)
    await ing.ingest_batch([_event("e1"), _event("e2")])
    got = await store.get("edit_events/e1")
    assert got is not None and got["event_id"] == "e1"


async def test_ingest_is_idempotent(store):
    ing = EditIngestor(store=store)
    await ing.ingest_batch([_event("e1")])
    await ing.ingest_batch([_event("e1")])
    keys: list[str] = []
    async for k, _ in store.list("edit_events/"):
        keys.append(k)
    assert keys == ["edit_events/e1"]
