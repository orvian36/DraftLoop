"""BlobStore protocol — raw bytes (PDFs, page images, model weights).

Default impl: local FS (added in Plan 1). Production swap: S3.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStore(Protocol):
    async def get(self, key: str) -> bytes: ...
    async def put(self, key: str, data: bytes) -> None: ...
    async def delete(self, key: str) -> None: ...
