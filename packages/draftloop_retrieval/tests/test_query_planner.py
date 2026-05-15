from unittest.mock import MagicMock

from draftloop_retrieval.query_planner import QueryPlanner
from draftloop_retrieval.slot_plan import SLOT_PLAN


def test_planner_emits_paraphrases_per_slot():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = "1. Who are the parties?\n2. Identify plaintiffs and defendants.\n3. Counsel involved.\n"
    fake.generate.return_value = resp
    planner = QueryPlanner(client=fake, model="gemini-2.5-flash", n=3)
    qs = planner.plan(SLOT_PLAN)
    assert set(qs.keys()) == {s.name for s in SLOT_PLAN}
    assert all(1 <= len(v) <= 5 for v in qs.values())
