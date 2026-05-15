"""Tesseract OCR fallback engine."""

from __future__ import annotations

from io import BytesIO

import pytesseract
from PIL import Image

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class TesseractEngine:
    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> ExtractedPage:
        img = Image.open(BytesIO(image_bytes))
        data = pytesseract.image_to_data(
            img, output_type=pytesseract.Output.DICT, config="--psm 6"
        )

        grouped: dict[tuple[int, int, int], list[int]] = {}
        for i in range(len(data["text"])):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            grouped.setdefault(key, []).append(i)

        lines: list[Line] = []
        for _, idxs in grouped.items():
            texts = [data["text"][i] for i in idxs]
            text = " ".join(t.strip() for t in texts if t and t.strip())
            if not text:
                continue
            confs = [int(c) for c in (data["conf"][i] for i in idxs) if int(c) >= 0]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
            xs = [int(data["left"][i]) for i in idxs]
            ys = [int(data["top"][i]) for i in idxs]
            xes = [int(data["left"][i] + data["width"][i]) for i in idxs]
            yes = [int(data["top"][i] + data["height"][i]) for i in idxs]
            lines.append(
                Line(
                    page=page,
                    text=text,
                    bbox=(min(xs), min(ys), max(xes), max(yes)),
                    confidence=avg_conf,
                    engine="tesseract",
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
            engine="tesseract",
        )
