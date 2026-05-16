"""EditIngestor — validate + persist raw EditEvents."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_core.storage import DocumentStore

from draftloop_edits.types import EditEvent


@dataclass
class EditIngestor:
    store: DocumentStore

    async def ingest_batch(self, events: list[EditEvent]) -> int:
        for evt in events:
            await self.store.put(f"edit_events/{evt.event_id}", evt.model_dump(mode="json"))
        return len(events)
