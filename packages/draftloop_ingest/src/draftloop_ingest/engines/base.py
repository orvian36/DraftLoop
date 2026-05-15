"""Engine protocols + the unified `ExtractedPage` shape they all return."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from draftloop_ingest.types import Line, PageClass


class ExtractedPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int                       # 1-based
    width_px: int
    height_px: int
    dpi: int
    class_: PageClass
    lines: list[Line]
    markdown: str                   # per-page markdown fragment, may be empty
    engine: str


@runtime_checkable
class DigitalExtractor(Protocol):
    def extract(self, path: str | Path, page_indices: list[int]) -> list[ExtractedPage]: ...


@runtime_checkable
class OcrEngine(Protocol):
    """Engines accept a rasterized page image and return an ExtractedPage."""

    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> ExtractedPage: ...
