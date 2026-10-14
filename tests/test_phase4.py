import pytest, httpx
from pathlib import Path
from linkiden.posts import parse_topics, next_topic, mark_topic, write_post, draft_problems, save_draft
from linkiden.tailor import allowed_skills
from linkiden.composio_client import Composio, PublishBlocked
from linkiden.media import _safe_target
from linkiden.report import build_report
from linkiden.schedule import cron_lines
from linkiden.db import DB

ROOT = Path(__file__).resolve().parents[1]; ALLOWED = allowed_skills(ROOT)
GOOD = ("I tested my RAG app the way I used to test APIs.\n\nIn week 4 I built a Self-RAG pipeline with LangGraph and FAISS. The first version answered "
        "everything, even questions it had no business answering.\n\nSo I wrote a golden dataset with DeepEval: normal questions, vague ones, and adversarial ones. "
        "Faithfulness caught answers that sounded right but were not in the retrieved text.\n\nEight years of QA taught me to ask what breaks first. Same habit, new system.\n\n"
        "How do you test your LLM apps?\n\n#GenAI #RAG #LangGraph #QA")

def test_topics_parse_and_mark():
    md = (ROOT / "context/topics_queue.md").read_text()
    t = parse_topics(md); assert len(t) >= 5 and t[0]["status"] == "todo"
    first = next_topic(md); assert first["repo"] == "week4_offline"
    assert next_topic(mark_topic(md, first["title"], "posted"))["title"] != first["title"]

class LLM:
    def __init__(self, outs): self.outs = list(outs); self.calls = 0
    def complete(self, s, u): self.calls += 1; return self.outs.pop(0) if len(self.outs) > 1 else self.outs[0]

def test_good_draft_passes():
    assert draft_problems(GOOD, ALLOWED) == []

def test_bad_drafts_flagged():
    assert any("cliche" in i for i in draft_problems(GOOD + " Excited to announce a game-changer", ALLOWED))
    assert any("unverified" in i for i in draft_problems(GOOD + " Deployed on Kubernetes", ALLOWED))
    assert any("hashtags" in i for i in draft_problems(GOOD.replace("#GenAI #RAG #LangGraph #QA", ""), ALLOWED))

def test_write_post_retries_until_valid():
    llm = LLM(["thrilled to share! game-changer " * 10, GOOD])
    text, issues = write_post(llm, {"title": "t"}, {"repo": "x"}, "", "", ALLOWED)
    assert text == GOOD and llm.calls == 2

def test_write_post_gives_up_with_issues():
    text, issues = write_post(LLM(["too short"]), {"title": "t"}, None, "", "", ALLOWED, retries=1)
    assert text is None and issues

def test_save_draft(tmp_path):
    (tmp_path / "outputs/drafts").mkdir(parents=True)
    assert save_draft(tmp_path, {"title": "Self-RAG / LangGraph!"}, "x").read_text() == "x"

def test_publish_requires_gate3():
    sent = []
    def handler(req): sent.append(req); return httpx.Response(200, json={"ok": True})
    c = Composio("k", client=httpx.Client(transport=httpx.MockTransport(handler))); db = DB(":memory:")
    with pytest.raises(PublishBlocked): c.post_linkedin(db, "topic", "text")
    assert sent == []
    db.log_approval("post", "topic", "reject")
    with pytest.raises(PublishBlocked): c.post_linkedin(db, "topic", "text")
    db.log_approval("post", "topic", "approve"); assert c.post_linkedin(db, "topic", "text") == {"ok": True} and len(sent) == 1
    assert sent[0].headers["x-api-key"] == "k"

def test_gmail_fetch_normalizes():
    h = lambda r: httpx.Response(200, json={"data": {"messages": [{"sender": "a@naukri.com", "subject": "s", "messageText": "b"}]}})
    assert Composio("k", client=httpx.Client(transport=httpx.MockTransport(h))).fetch_gmail() == [{"sender": "a@naukri.com", "subject": "s", "body": "b"}]

@pytest.mark.parametrize("u,ok", [("http://localhost:8501", True), ("https://github.com/vino2203/x", True), ("http://169.254.169.254/latest", False), ("file:///etc/passwd", False), ("https://evil.com", False)])
def test_media_url_safety(u, ok): assert _safe_target(u) is ok

def test_report_and_cron():
    db = DB(":memory:"); j, _ = db.add_job("n", "t", "c", "l", "u"); db.set_status(j, "replied")
    assert "replied: 1" in build_report(db)
    lines = cron_lines({"job_discovery": {"every_days": 1, "time": "08:00"}, "linkedin_posts": {"every_days": 2, "time": "09:00"}, "daily_report": {"time": "20:00"}}, Path("/p"))
    assert lines[0].startswith("0 8 * * *") and lines[1].startswith("0 9 */2 * *") and lines[2].startswith("0 20")
