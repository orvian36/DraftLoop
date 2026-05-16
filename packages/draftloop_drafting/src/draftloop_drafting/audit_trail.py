"""Persist audit_trail.json next to each draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditTrailWriter:
    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        matter_id: str,
        draft_id: str,
        model: str,
        drafter_mode: str,
        prompt_hash: str,
        cache_name: str | None,
        retrieved_chunks: list[dict],
        exemplars_used: list[dict],
        style_rules_active: list[str],
        verification: dict[str, Any],
        token_usage: dict[str, int],
        cost_usd: float,
        duration_ms: int,
        ingest_versions: dict[str, str],
    ) -> str:
        payload = {
            "matter_id": matter_id,
            "draft_id": draft_id,
            "model": model,
            "drafter_mode": drafter_mode,
            "prompt_hash": prompt_hash,
            "cache_name": cache_name,
            "retrieved_chunks": retrieved_chunks,
            "exemplars_used": exemplars_used,
            "style_rules_active": style_rules_active,
            "verification": verification,
            "token_usage": token_usage,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "ingest_versions": ingest_versions,
        }
        out_dir = self._root / matter_id / draft_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "audit_trail.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
