"""Process-level singletons. Avoid re-creating heavy components per request."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from draftloop_core.config import get_settings
from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex
from draftloop_core.storage.local_blob_store import LocalBlobStore
from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore


@lru_cache(maxsize=1)
def document_store() -> SqliteDocumentStore:
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    return SqliteDocumentStore(Path(settings.data_dir) / "draftloop.db")


@lru_cache(maxsize=1)
def vector_index() -> ChromaVectorIndex:
    settings = get_settings()
    return ChromaVectorIndex(persist_path=str(Path(settings.data_dir) / "chroma"))


@lru_cache(maxsize=1)
def bm25_index() -> RankBm25LexicalIndex:
    settings = get_settings()
    return RankBm25LexicalIndex(persist_path=str(Path(settings.data_dir) / "bm25"))


@lru_cache(maxsize=1)
def blob_store() -> LocalBlobStore:
    settings = get_settings()
    return LocalBlobStore(root=str(Path(settings.data_dir) / "blob"))


def reset_singletons() -> None:
    for fn in (document_store, vector_index, bm25_index, blob_store):
        fn.cache_clear()
