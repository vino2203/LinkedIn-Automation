"""Track 2 apply step: Gate-2-approved jobs -> tailor -> guard -> Applier (portal session). Usage: python -m linkiden.run_apply [--dry-run]
Uploads your original resume PDF; the tailored text is saved to outputs/tailored_resumes for review and used for cover notes."""
from __future__ import annotations
import argparse
import yaml
from .config import ROOT, load_settings
from .db import DB
from .llm import make_llm
from .tailor import allowed_skills, tailor_resume
from .applier import Applier, load_contact

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    s = load_settings(); db = DB(ROOT / "data" / "jobs.db"); allowed = allowed_skills(ROOT)
    models = yaml.safe_load((ROOT / "config" / "agents.yaml").read_text()); llm = make_llm(s.secrets, models["tailor"]["model"])
    master = (ROOT / "context/resume.md").read_text(); ev = (ROOT / "context/skills_evidence.md").read_text()
    pdfs = sorted((ROOT / "resume").glob("*.pdf")); pdf = str(pdfs[0]) if pdfs else None
    gate = None
    if not a.dry_run:
        from .gate import TelegramGate
        gate = TelegramGate(s.secret("TELEGRAM_BOT_TOKEN"), s.secret("TELEGRAM_CHAT_ID"), db, 24)
    applier = Applier(db, s, gate, load_contact(ROOT), ROOT)
    for row in db.jobs("approved"):
        job = dict(row)
        text, tailored = tailor_resume(llm, master, ev, job, allowed)
        (ROOT / "outputs/tailored_resumes" / f"{job['id']}.md").write_text(text)
        if a.dry_run:
            print(job["title"], "@", job["company"], "->", applier.apply(job, text, allowed)); continue
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(f".playwright-session/{job['source']}", headless=False)
            page = ctx.new_page(); page.goto(job["url"], wait_until="domcontentloaded"); page.wait_for_timeout(3000)
            try: print(job["title"], "->", applier.apply(job, text, allowed, page=page, resume_path=pdf))
            except RuntimeError as e: gate.notify(f"Stopped on {job['company']}: {e}")
            ctx.close()

if __name__ == "__main__":
    main()
