"""Default BlobStore impl: keys map directly to file paths under a root dir."""

from __future__ import annotations

import asyncio
from pathlib import Path


class LocalBlobStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if any(seg == ".." for seg in Path(key).parts):
            raise ValueError(f"invalid key {key!r}: '..' segments not allowed")
        return self._root / key

    async def get(self, key: str) -> bytes:
        p = self._path(key)
        return await asyncio.to_thread(p.read_bytes)

    async def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(p.write_bytes, data)

    async def delete(self, key: str) -> None:
        p = self._path(key)
        await asyncio.to_thread(p.unlink, missing_ok=True)
