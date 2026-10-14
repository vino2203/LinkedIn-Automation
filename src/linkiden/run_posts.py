"""Track 1: pick topic -> GitHub brief -> write -> validate -> Gate 3 -> post. Usage: python -m linkiden.run_posts [--dry-run]"""
from __future__ import annotations
import argparse, datetime
import yaml
from .config import ROOT, load_settings
from .db import DB
from .github_agent import repo_brief
from .llm import make_llm
from .posts import next_topic, mark_topic, write_post, save_draft
from .tailor import allowed_skills

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    s = load_settings(); db = DB(ROOT / "data" / "jobs.db")
    q = ROOT / "context" / "topics_queue.md"; md = q.read_text(); topic = next_topic(md)
    if not topic: raise SystemExit("no todo topics left")
    brief = None
    if topic.get("repo") and s.secrets.get("GITHUB_TOKEN"):
        try: brief = repo_brief("vino2203", topic["repo"], s.secret("GITHUB_TOKEN"))
        except Exception as e: print("github brief failed:", type(e).__name__)
    models = yaml.safe_load((ROOT / "config" / "agents.yaml").read_text())
    llm = make_llm(s.secrets, models["a2_writer_demo_maker"]["model"])
    text, issues = write_post(llm, topic, brief, (ROOT / "context/voice.md").read_text(), (ROOT / "context/skills_evidence.md").read_text(), allowed_skills(ROOT))
    if not text: raise SystemExit(f"could not produce a valid draft: {issues}")
    path = save_draft(ROOT, topic, text); print("draft saved:", path)
    if a.dry_run: print(text); return
    from .gate import TelegramGate; from .composio_client import Composio
    gate = TelegramGate(s.secret("TELEGRAM_BOT_TOKEN"), s.secret("TELEGRAM_CHAT_ID"), db, s.prefs.get("approval_expiry_hours", 24))
    if gate.ask("post", topic["title"], f"POST DRAFT ({topic['title']}):\n\n{text}") != "approve":
        db.log_approval("post-result", topic["title"], "not-approved"); return
    Composio(s.secret("COMPOSIO_API_KEY")).post_linkedin(db, topic["title"], text)
    q.write_text(mark_topic(md, topic["title"], "posted"))
    with open(ROOT / "data" / "posts_log.md", "a") as f: f.write(f"- {datetime.date.today()} | {topic['title']} | posted\n")
    gate.notify(f"Posted: {topic['title']}")

if __name__ == "__main__":
    main()
