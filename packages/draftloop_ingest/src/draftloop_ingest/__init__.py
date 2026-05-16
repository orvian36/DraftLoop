"""DraftLoop document ingestion + OCR.

Public API:
    IngestPipeline, IngestRequest, IngestResult, Page, Line, NeedsReviewSpan, DocStatus
"""

from draftloop_ingest.pipeline import IngestPipeline
from draftloop_ingest.types import (
    DocStatus,
    IngestRequest,
    IngestResult,
    Line,
    NeedsReviewSpan,
    Page,
)

__all__ = [
    "DocStatus",
    "IngestPipeline",
    "IngestRequest",
    "IngestResult",
    "Line",
    "NeedsReviewSpan",
    "Page",
]
__version__ = "0.1.0"
