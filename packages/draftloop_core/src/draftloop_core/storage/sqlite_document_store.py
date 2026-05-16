"""Default DocumentStore impl backed by SQLite (via aiosqlite).

Production swap target: PostgresDocumentStore (not implemented here).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiosqlite

from draftloop_core.errors import StorageError


class SqliteDocumentStore:
    """File-backed JSON-blob store keyed by string. Async API for FastAPI compatibility."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def init_schema(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def get(self, key: str) -> Any | None:
        async with (
            aiosqlite.connect(self._db_path) as db,
            db.execute("SELECT value FROM kv WHERE key = ?", (key,)) as cur,
        ):
            row = await cur.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"corrupt value at {key!r}",
                code="STORAGE_CORRUPT_VALUE",
            ) from exc

    async def put(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO kv(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, payload),
            )
            await db.commit()

    async def delete(self, key: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM kv WHERE key = ?", (key,))
            await db.commit()

    async def list(self, prefix: str = "") -> AsyncIterator[tuple[str, Any]]:
        like = f"{prefix}%"
        async with (
            aiosqlite.connect(self._db_path) as db,
            db.execute("SELECT key, value FROM kv WHERE key LIKE ? ORDER BY key", (like,)) as cur,
        ):
            async for row in cur:
                yield row[0], json.loads(row[1])
