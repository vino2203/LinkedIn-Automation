"""Daily job run: discover -> dedupe -> triage -> Gate 1 / Gate 2 over Telegram. Does NOT apply (applier is a later phase).
Usage: python -m linkiden.run_daily [--dry-run]"""
from __future__ import annotations
import argparse
import yaml
from .config import ROOT, load_settings
from .db import DB
from .gate import TelegramGate, job_card
from .pipeline import triage, apply_db_approvals, set_designation
from .roles import role_status
from .scorer import LLMScorer
from .llm import make_llm, _ClientAdapter
from .discovery import naukri


def handle(db, gate, settings, scorer, job) -> str:
    outcome = triage(db, job, settings, scorer)
    if outcome == "needs_gate1":
        _, canon = role_status(job["title"], settings.roles)
        subject = canon or job["title"]
        decision = gate.ask("designation", subject, f"New designation: '{subject}'\nSeen in: {job['title']} @ {job['company']}\nApprove this designation?")
        if decision == "approve":
            if canon:
                set_designation(settings, canon, decision)
            outcome = triage(db, job, settings, scorer) if canon else "needs_gate2"
        else:
            db.set_status(job["id"], "rejected", reasons="designation rejected/expired")
            return "rejected"
    if outcome == "needs_gate2":
        row = db.conn.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
        decision = gate.ask("job", job["id"], job_card(dict(row)))
        if decision == "approve":
            db.set_status(job["id"], "approved"); return "approved"
        db.set_status(job["id"], "rejected" if decision == "reject" else "expired"); return decision
    return outcome


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); args = ap.parse_args()
    s = load_settings()
    missing = s.missing_secrets()
    if missing and not args.dry_run:
        raise SystemExit(f"Missing in config/.env: {', '.join(missing)}")
    db = DB(ROOT / "data" / "jobs.db")
    apply_db_approvals(s, db)
    models = yaml.safe_load((ROOT / "config" / "agents.yaml").read_text())
    scorer = LLMScorer(_ClientAdapter(make_llm(s.secrets, models["matcher_scorer"]["model"])), models["matcher_scorer"]["model"], ROOT)
    roles = [r["title"] for r in s.roles["roles"] if r["status"] != "rejected"]
    jobs = naukri.discover(roles, [l for l in s.prefs["locations"] if l.lower() != "remote"])
    new = []
    for j in jobs:
        j["id"], created = db.add_job(j["source"], j["title"], j["company"], j["location"], j["url"], j["description"])
        if created: new.append(j)
    print(f"found {len(jobs)} listings, {len(new)} new")
    if args.dry_run:
        for j in new[:10]: print("-", j["title"], "@", j["company"])
        return
    gate = TelegramGate(s.secret("TELEGRAM_BOT_TOKEN"), s.secret("TELEGRAM_CHAT_ID"), db, s.prefs.get("approval_expiry_hours", 24))
    results = [handle(db, gate, s, scorer, j) for j in new]
    gate.notify(f"Daily run: {len(new)} new, {results.count('approved')} approved, {results.count('rejected')} rejected.")


if __name__ == "__main__":
    main()
