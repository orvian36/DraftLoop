"""DocumentStore protocol — generic key/value persistence for domain objects.

Default impl: SQLite (added in Plan 1). Production swap: Postgres.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DocumentStore(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def put(self, key: str, value: Any) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def list(self, prefix: str = "") -> AsyncIterator[tuple[str, Any]]: ...
