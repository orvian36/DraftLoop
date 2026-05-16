import json
from unittest.mock import MagicMock

from draftloop_drafting.generator import Generator
from draftloop_drafting.schema import CaseFactSummary


def test_single_call_parses_json_into_schema():
    fake = MagicMock()
    summary = {
        "parties": [
            {
                "sentence_id": "s_1",
                "text": "Acme vs Widgets",
                "citations": [{"chunk_id": "c1", "quote": "Acme"}],
                "confidence": "high",
            }
        ],
        "jurisdiction": [],
        "key_dates": [],
        "claims": [],
        "relief_sought": [],
        "procedural_posture": [],
        "key_evidence": [],
    }
    resp = MagicMock()
    resp.text = json.dumps(summary)
    resp.parsed = None
    resp.usage = MagicMock(input_tokens=1000, output_tokens=200, cached_tokens=0)
    fake.generate.return_value = resp

    g = Generator(client=fake, model="gemini-2.5-pro", mode="single_call")
    out, usage = g.generate(system_prompt="sys", user_prompt="usr")
    assert isinstance(out, CaseFactSummary)
    assert out.parties[0].text == "Acme vs Widgets"
    assert usage.input_tokens == 1000
