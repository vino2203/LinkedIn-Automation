"""Turn fetched Gmail messages into job status updates. Fetching (Composio) is injected; this is pure logic."""
from __future__ import annotations
from .db import DB
from .gmail_agent import classify, extract_otp

def process_messages(db: DB, messages: list[dict]) -> dict:
    """messages: [{'sender','subject','body'}]. Matches by company name against applied jobs. Returns counts."""
    out = {"confirmation": 0, "recruiter_reply": 0, "ignored": 0}
    applied = db.conn.execute("SELECT id, company, status FROM jobs WHERE status IN ('applied','confirmed')").fetchall()
    for m in messages:
        kind = classify(m["sender"], m["subject"], m["body"])
        if kind not in ("confirmation", "recruiter_reply"):
            out["ignored"] += 1; continue
        text = f"{m['subject']} {m['body']}".lower()
        match = next((j for j in applied if j["company"] and j["company"].lower() in text), None)
        if not match:
            out["ignored"] += 1; continue
        db.set_status(match["id"], "confirmed" if kind == "confirmation" else "replied")
        out[kind] += 1
    return out

def latest_otp(messages: list[dict]) -> str | None:
    for m in messages:  # newest first
        otp = extract_otp(m["sender"], m["subject"], m["body"])
        if otp: return otp
    return None
