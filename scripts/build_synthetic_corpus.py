#!/usr/bin/env python3
"""Generate DraftLoop's deterministic synthetic corpus.

Writes PDF variants into ``data/synthetic/`` (gitignored). Six files:

  digital-native:
    complaint.pdf, motion.pdf, answer.pdf, order.pdf
  scanned (rasterised + re-embedded as page images):
    complaint_scan.pdf, motion_scan.pdf

Re-running is idempotent: the same templates produce byte-identical outputs.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from pypdfium2 import PdfDocument
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DATA_DIR = Path("data/synthetic")
TEMPLATES = {
    "complaint": {
        "title": "COMPLAINT",
        "body": (
            "Plaintiff Acme Corp. brings this action against Defendant Widgets Inc. "
            "for breach of the SaaS agreement executed on 2024-03-14 in Illinois. "
            "Plaintiff seeks damages in the amount of $250,000 and injunctive relief. "
            "The Court has jurisdiction under 28 U.S.C. Section 1331."
        ),
    },
    "motion": {
        "title": "MOTION TO DISMISS",
        "body": (
            "Defendant Widgets Inc. moves to dismiss the Complaint pursuant to Rule 12(b)(6) "
            "for failure to state a claim. The motion is set for hearing on 2026-06-15."
        ),
    },
    "answer": {
        "title": "ANSWER",
        "body": (
            "Defendant Widgets Inc. responds to each paragraph of the Complaint. "
            "Paragraph 1 is admitted. Paragraph 2 is denied. Paragraph 3 is denied for lack "
            "of knowledge sufficient to form a belief as to its truth."
        ),
    },
    "order": {
        "title": "ORDER",
        "body": (
            "The Court, having considered the Motion to Dismiss and the Response, hereby "
            "GRANTS in part and DENIES in part. So ordered on 2026-05-20."
        ),
    },
}


def _draw_digital(path: Path, title: str, body: str) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, title)
    c.setFont("Helvetica", 12)
    y = 690
    for line in body.split(". "):
        if not line:
            continue
        c.drawString(72, y, line.strip() + ".")
        y -= 18
    c.showPage()
    c.save()


def _rasterize_to_pdf(src: Path, dst: Path, dpi: int = 300) -> None:
    """Convert ``src`` PDF to a scanned-style PDF where each page is a PNG image."""
    pdf = PdfDocument(str(src))
    try:
        c = canvas.Canvas(str(dst), pagesize=letter)
        for page in pdf:
            scale = dpi / 72.0
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            buf.seek(0)
            tmp_png = dst.with_suffix(".tmp.png")
            tmp_png.write_bytes(buf.getvalue())
            c.drawImage(str(tmp_png), 0, 0, width=letter[0], height=letter[1])
            c.showPage()
            tmp_png.unlink(missing_ok=True)
        c.save()
    finally:
        pdf.close()


def build(force: bool = False) -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for name, meta in TEMPLATES.items():
        dst = DATA_DIR / f"{name}.pdf"
        if not dst.exists() or force:
            _draw_digital(dst, meta["title"], meta["body"])
        produced.append(dst)
    for name in ["complaint", "motion"]:
        src = DATA_DIR / f"{name}.pdf"
        dst = DATA_DIR / f"{name}_scan.pdf"
        if not dst.exists() or force:
            _rasterize_to_pdf(src, dst, dpi=300)
        produced.append(dst)
    return produced


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    produced = build(force=args.force)
    for p in produced:
        print(p)
    print(f"==> {len(produced)} files in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
