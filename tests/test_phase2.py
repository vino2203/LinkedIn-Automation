from types import SimpleNamespace
from linkiden.scorer import parse_result, LLMScorer
from linkiden.discovery.naukri import normalize, search_url
from linkiden.db import DB
from linkiden.config import Settings
from linkiden.run_daily import handle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_parse_result():
    assert parse_result('x {"score": 93, "reasons": "good", "missing": ["AWS"]} y') == (93, "good | missing: AWS")
    assert parse_result('{"score": 250}')[0] == 100
    assert parse_result("no json")[0] == 0

def test_scorer_uses_client():
    calls = {}
    class C:
        class messages:
            @staticmethod
            def create(**kw):
                calls.update(kw); return SimpleNamespace(content=[SimpleNamespace(text='{"score": 91, "reasons": "ok", "missing": []}')])
    sc = LLMScorer(C, "m", ROOT)
    assert sc({"title": "GenAI Engineer", "company": "A", "description": "d"})[0] == 91
    assert "VERIFIED_SKILLS" in calls["messages"][0]["content"]

def test_naukri_helpers():
    assert search_url("GenAI Engineer", "Chennai").endswith("/genai-engineer-jobs-in-chennai")
    assert normalize({"title": "", "company": "x"}) is None
    assert normalize({"title": "T", "company": "C"})["source"] == "naukri"

class FakeGate:
    def __init__(self, answers): self.answers, self.asked = list(answers), []
    def ask(self, gate, subject, text): self.asked.append(gate); return self.answers.pop(0)

def _setup(status):
    s = Settings({}, {"min_match_score": 90, "locations": ["Chennai"]}, {"roles": [{"title": "RAG Engineer", "status": status}], "exclude_titles": []})
    db = DB(":memory:")
    jid, _ = db.add_job("naukri", "RAG Engineer", "Acme", "Chennai", "u")
    return s, db, {"id": jid, "title": "RAG Engineer", "company": "Acme", "location": "Chennai", "url": "u"}

def test_gate1_then_gate2_flow():
    s, db, job = _setup("pending"); g = FakeGate(["approve", "approve"])
    assert handle(db, g, s, lambda j: (95, "ok"), job) == "approved"
    assert g.asked == ["designation", "job"]

def test_gate1_reject_blocks_job():
    s, db, job = _setup("pending"); g = FakeGate(["reject"])
    assert handle(db, g, s, lambda j: (95, "ok"), job) == "rejected" and g.asked == ["designation"]

def test_low_score_never_asks():
    s, db, job = _setup("approved"); g = FakeGate([])
    assert handle(db, g, s, lambda j: (60, "weak"), job) == "rejected" and g.asked == []
