"""IngestPipeline — top-level orchestrator for ingestion.

Decides per page which engine to invoke, normalizes outputs, emits
IngestResult.
"""

from __future__ import annotations

import time
from pathlib import Path

from draftloop_core.obs import get_logger, traced

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.engines.pymupdf4llm_engine import Pdf4llmExtractor
from draftloop_ingest.markdown_assembler import assemble_markdown
from draftloop_ingest.probe import probe_pdf
from draftloop_ingest.raster import rasterize_page
from draftloop_ingest.types import (
    IngestRequest,
    IngestResult,
    NeedsReviewSpan,
    Page,
)

logger = get_logger("draftloop.ingest")

INGEST_VERSION = "v1"


class IngestPipeline:
    def __init__(
        self,
        *,
        digital_extractor: Pdf4llmExtractor | None = None,
        paddle_engine_factory=None,
        tesseract_engine_factory=None,
    ) -> None:
        self._digital = digital_extractor or Pdf4llmExtractor()
        self._paddle_factory = paddle_engine_factory
        self._tesseract_factory = tesseract_engine_factory
        self._paddle = None
        self._tesseract = None

    def _get_paddle(self):
        if self._paddle is None:
            if self._paddle_factory is not None:
                self._paddle = self._paddle_factory()
            else:
                try:
                    from draftloop_ingest.engines.paddle_engine import PaddleEngine

                    self._paddle = PaddleEngine()
                except Exception as exc:
                    logger.warning("ingest.paddle_unavailable", error=str(exc))
                    self._paddle = False
        return self._paddle or None

    def _get_tesseract(self):
        if self._tesseract is None:
            if self._tesseract_factory is not None:
                self._tesseract = self._tesseract_factory()
            else:
                try:
                    from draftloop_ingest.engines.tesseract_engine import TesseractEngine

                    self._tesseract = TesseractEngine()
                except Exception as exc:
                    logger.warning("ingest.tesseract_unavailable", error=str(exc))
                    self._tesseract = False
        return self._tesseract or None

    @traced("draftloop.ingest.run")
    def run(self, req: IngestRequest) -> IngestResult:
        start = time.monotonic()
        doc_id = req.doc_id or Path(req.source_path).stem
        try:
            probes = probe_pdf(req.source_path)
        except Exception as exc:
            return IngestResult(
                doc_id=doc_id,
                source_path=req.source_path,
                pages=[],
                markdown="",
                needs_review_spans=[],
                aggregate_confidence=0.0,
                engines_used={},
                duration_ms=int((time.monotonic() - start) * 1000),
                ingest_version=INGEST_VERSION,
                failed=True,
                fail_reason=f"probe_failed: {exc}",
            )

        digital_indices = [p.page_index for p in probes if p.has_text_layer]
        scanned_indices = [p.page_index for p in probes if not p.has_text_layer]

        extracted: dict[int, ExtractedPage] = {}
        engines_used: dict[int, list[str]] = {}

        if digital_indices:
            for page in self._digital.extract(req.source_path, digital_indices):
                extracted[page.page] = page
                engines_used[page.page] = ["pymupdf4llm"]

        for idx in scanned_indices:
            page_no = idx + 1
            image_bytes = rasterize_page(req.source_path, idx, dpi=300)
            from draftloop_ingest.preprocess import preprocess_image

            preprocessed = preprocess_image(image_bytes)

            probe = probes[idx]
            page_obj: ExtractedPage | None = None
            engines_for_page: list[str] = []

            paddle = self._get_paddle() if req.enable_paddle else None
            if paddle is not None:
                try:
                    page_obj = paddle.ocr(
                        image_bytes=preprocessed,
                        page=page_no,
                        width_px=probe.width_px,
                        height_px=probe.height_px,
                        dpi=300,
                    )
                    engines_for_page.append("paddleocr")
                except Exception as exc:
                    logger.warning("ingest.paddle_failed", page=page_no, error=str(exc))

            if (page_obj is None or not page_obj.lines) and req.enable_tesseract_fallback:
                tess = self._get_tesseract()
                if tess is not None:
                    try:
                        page_obj = tess.ocr(
                            image_bytes=preprocessed,
                            page=page_no,
                            width_px=probe.width_px,
                            height_px=probe.height_px,
                            dpi=300,
                        )
                        engines_for_page.append("tesseract")
                    except Exception as exc:
                        logger.warning("ingest.tesseract_failed", page=page_no, error=str(exc))

            if page_obj is not None:
                extracted[page_no] = page_obj
                engines_used[page_no] = engines_for_page

        pages_list = [extracted[k] for k in sorted(extracted)]
        markdown = assemble_markdown(pages_list)

        needs_review_spans: list[NeedsReviewSpan] = []
        confs: list[float] = []
        emitted_pages: list[Page] = []
        for ep in pages_list:
            page_conf = (
                sum(line.confidence for line in ep.lines) / len(ep.lines) if ep.lines else 0.0
            )
            confs.append(page_conf)
            page_needs_review = any(line.needs_review for line in ep.lines)
            for line in ep.lines:
                if line.needs_review:
                    needs_review_spans.append(
                        NeedsReviewSpan(
                            page=ep.page,
                            bbox=line.bbox,
                            text=line.text,
                            confidence=line.confidence,
                            reason="low_ocr_conf",
                        )
                    )
            emitted_pages.append(
                Page(
                    page=ep.page,
                    width_px=ep.width_px,
                    height_px=ep.height_px,
                    dpi=ep.dpi,
                    class_=ep.class_,
                    engines_used=engines_used.get(ep.page, []),
                    lines=ep.lines,
                    needs_review=page_needs_review,
                )
            )

        aggregate = sum(confs) / len(confs) if confs else 0.0
        return IngestResult(
            doc_id=doc_id,
            source_path=req.source_path,
            pages=emitted_pages,
            markdown=markdown,
            needs_review_spans=needs_review_spans,
            aggregate_confidence=aggregate,
            engines_used=engines_used,
            duration_ms=int((time.monotonic() - start) * 1000),
            ingest_version=INGEST_VERSION,
        )
