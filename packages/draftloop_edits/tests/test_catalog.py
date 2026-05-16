from datetime import datetime
from unittest.mock import MagicMock

import numpy as np

from draftloop_edits.catalog import RuleCatalog
from draftloop_edits.types import InducedRule


def test_catalog_returns_empty_when_below_min_size():
    embedder = MagicMock()
    cat = RuleCatalog(
        embedder=embedder,
        flash_client=MagicMock(),
        flash_model="gemini-2.5-flash",
        min_cluster_size=3,
    )
    rules = [
        InducedRule(
            rule_id=f"r{i}",
            event_id=f"e{i}",
            text=f"rule {i}",
            trust_weight=1.0,
            pinned=False,
            created_at=datetime.utcnow(),
        )
        for i in range(2)
    ]
    assert cat.cluster(rules) == []


def test_catalog_handles_missing_hdbscan_gracefully(monkeypatch):
    """When hdbscan isn't installed, cluster() returns [] instead of erroring."""
    import sys

    monkeypatch.setitem(sys.modules, "hdbscan", None)
    embedder = MagicMock()
    embedder.embed_documents.return_value = [list(np.random.rand(1536)) for _ in range(5)]
    cat = RuleCatalog(
        embedder=embedder,
        flash_client=MagicMock(),
        flash_model="gemini-2.5-flash",
        min_cluster_size=3,
    )
    rules = [
        InducedRule(
            rule_id=f"r{i}",
            event_id=f"e{i}",
            text=f"rule {i}",
            trust_weight=1.0,
            pinned=False,
            created_at=datetime.utcnow(),
        )
        for i in range(5)
    ]
    # With hdbscan-None monkey patched, import fails -> returns [].
    assert cat.cluster(rules) == []
