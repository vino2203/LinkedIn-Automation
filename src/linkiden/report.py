"""Daily status report from jobs.db."""
from __future__ import annotations
from .db import DB, STATUSES

def build_report(db: DB) -> str:
    counts = {s: db.conn.execute("SELECT COUNT(*) FROM jobs WHERE status=?", (s,)).fetchone()[0] for s in STATUSES}
    lines = ["Daily report"] + [f"{s}: {n}" for s, n in counts.items() if n]
    lines.append(f"applied today: {db.applied_today()}")
    replied = db.jobs("replied")
    lines += [f"reply: {r['title']} @ {r['company']}" for r in replied[:5]]
    return "\n".join(lines)


if __name__ == "__main__":
    from .config import ROOT, load_settings
    from .gate import TelegramGate
    s = load_settings(); db = DB(ROOT / "data" / "jobs.db")
    TelegramGate(s.secret("TELEGRAM_BOT_TOKEN"), s.secret("TELEGRAM_CHAT_ID"), db).notify(build_report(db))
