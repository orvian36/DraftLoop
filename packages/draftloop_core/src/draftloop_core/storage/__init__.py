"""Storage protocols + reference implementations for DraftLoop.

Default impls (added by Plans 1+2): SQLite (DocumentStore), Chroma (VectorIndex),
local FS (BlobStore). Production swaps are config-driven.
"""

from draftloop_core.storage.blob_store import BlobStore
from draftloop_core.storage.document_store import DocumentStore
from draftloop_core.storage.vector_index import VectorHit, VectorIndex, VectorItem

__all__ = [
    "BlobStore",
    "DocumentStore",
    "VectorIndex",
    "VectorItem",
    "VectorHit",
]
