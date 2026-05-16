#!/usr/bin/env python3
"""One-command demo seeder.

Steps:
  1. Build the synthetic corpus (if not already present).
  2. Upload each synthetic PDF to matter M-001 via BlobStore + DocumentStore.

Idempotent — re-running produces the same end state.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


async def _seed(force: bool) -> None:
    # The wiring uses get_settings(), which requires GEMINI_API_KEY to validate.
    # For the seed-only path we don't actually call Gemini, so any value is fine.
    os.environ.setdefault(
        "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "demo-not-used")
    )
    from draftloop_core.config import get_settings
    get_settings.cache_clear()

    import build_synthetic_corpus as corpus_gen
    corpus_gen.build(force=force)

    from draftloop_api.wiring import blob_store, document_store, reset_singletons
    reset_singletons()
    store = document_store()
    await store.init_schema()
    blob = blob_store()

    for pdf in sorted((REPO_ROOT / "data" / "synthetic").glob("*.pdf")):
        key = f"M-001/{pdf.name}"
        await blob.put(key, pdf.read_bytes())
        await store.put(
            f"docs/M-001/{pdf.name}",
            {"status": "uploaded", "filename": pdf.name, "blob_key": key},
        )
        print(f"==> uploaded {pdf.name}")

    print("==> demo seed complete. Matter M-001 ready.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate synthetic PDFs")
    args = parser.parse_args()
    asyncio.run(_seed(force=args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
