from linkiden.db import DB
from linkiden.roles import role_status, location_ok
from linkiden.pipeline import triage
from linkiden.config import Settings

ROLES = {"roles": [{"title": "GenAI Engineer", "status": "approved"}, {"title": "RAG Engineer", "status": "pending"}],
         "exclude_titles": ["Data Scientist", "Intern"]}
PREFS = {"min_match_score": 90, "locations": ["Chennai", "Remote"]}
S = Settings({}, PREFS, ROLES)

def mk(db, title, loc="Chennai"):
    jid, _ = db.add_job("naukri", title, "Acme", loc, "http://x")
    return {"id": jid, "title": title, "location": loc}

def test_dedupe():
    db = DB(":memory:")
    assert db.add_job("a", "GenAI Engineer", "Acme", "Chennai", "u")[1] is True
    assert db.add_job("b", "genai engineer", "ACME", "chennai", "u2")[1] is False

def test_role_status():
    assert role_status("Senior GenAI Engineer", ROLES) == ("approved", "GenAI Engineer")
    assert role_status("Data Scientist", ROLES)[0] == "excluded"
    assert role_status("Chef", ROLES)[0] == "unknown"
    assert role_status("RAG Engineer II", ROLES)[0] == "pending"

def test_location():
    assert location_ok("Chennai, TN", PREFS) and not location_ok("Pune", PREFS)

def test_triage_paths():
    db = DB(":memory:")
    hi = lambda j: (95, "ok"); lo = lambda j: (70, "weak")
    assert triage(db, mk(db, "GenAI Engineer"), S, hi) == "needs_gate2"
    assert triage(db, mk(db, "RAG Engineer"), S, hi) == "needs_gate1"
    assert triage(db, mk(db, "Prompt Wizard"), S, hi) == "needs_gate1"
    assert triage(db, mk(db, "GenAI Engineer Intern"), S, hi) == "rejected"
    assert triage(db, mk(db, "GenAI Engineer II", "Pune"), S, hi) == "rejected"
    assert triage(db, mk(db, "GenAI Engineer III"), S, lo) == "rejected"

def test_approval_memory():
    db = DB(":memory:"); db.log_approval("designation", "RAG Engineer", "approve")
    assert db.approved_before("designation", "RAG Engineer") == "approve"
