"""PaddleOCR PP-OCRv5 engine (default scanned-page extractor).

Optional dependency: paddleocr is heavy (PaddlePaddle, GPU build of CUDA on some
platforms). Installation isn't pinned in this package — install via `pip install paddleocr`
when needed. If unavailable, IngestPipeline falls back to TesseractEngine.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class PaddleEngine:
    """Thin wrapper around paddleocr.PaddleOCR.

    First instantiation downloads model weights and caches them.
    """

    def __init__(self) -> None:
        # Lazy import: importing paddleocr triggers paddlepaddle to load, which is
        # expensive (~600MB) and may fail on some platforms.
        from paddleocr import PaddleOCR  # type: ignore[import-not-found]

        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )

    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> ExtractedPage:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        result = self._ocr.ocr(arr, cls=True)
        page_result = result[0] if result and isinstance(result[0], list) else []
        lines: list[Line] = []
        for box, (text, score) in page_result:
            if not text:
                continue
            xs = [int(p[0]) for p in box]
            ys = [int(p[1]) for p in box]
            lines.append(
                Line(
                    page=page,
                    text=text,
                    bbox=(min(xs), min(ys), max(xs), max(ys)),
                    confidence=float(score),
                    engine="paddleocr",
                )
            )
        return ExtractedPage(
            page=page,
            width_px=width_px,
            height_px=height_px,
            dpi=dpi,
            class_="clean_scan",
            lines=lines,
            markdown="\n".join(line.text for line in lines),
            engine="paddleocr",
        )
