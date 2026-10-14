"""Triage: raw job -> rejected | awaiting Gate 1 | awaiting Gate 2. Pure logic; scoring is injected (LLM later)."""
from __future__ import annotations
from typing import Callable
from .db import DB
from .roles import role_status, location_ok

Scorer = Callable[[dict], tuple[int, str]]  # job -> (score 0-100, reasons)


def triage(db: DB, job: dict, settings, scorer: Scorer) -> str:
    verdict, canon = role_status(job["title"], settings.roles)
    jid = job["id"]
    if verdict in ("excluded", "rejected"):
        db.set_status(jid, "rejected", reasons=f"role {verdict}")
        return "rejected"
    if not location_ok(job.get("location", ""), settings.prefs):
        db.set_status(jid, "rejected", reasons="location")
        return "rejected"
    score, reasons = scorer(job)
    if score < settings.min_score:
        db.set_status(jid, "rejected", score=score, reasons=reasons)
        return "rejected"
    if verdict in ("unknown", "pending"):
        db.set_status(jid, "scored", score=score, reasons=reasons)
        return "needs_gate1"          # designation must be approved before any apply
    db.set_status(jid, "awaiting_approval", score=score, reasons=reasons)
    return "needs_gate2"


def apply_db_approvals(settings, db: DB) -> None:
    """Fold previously recorded designation decisions (Gate 1) into the in-memory role list."""
    for r in settings.roles.get("roles", []):
        d = db.approved_before("designation", r["title"])
        if d:
            r["status"] = "approved" if d == "approve" else "rejected"


def set_designation(settings, title: str, decision: str) -> None:
    for r in settings.roles["roles"]:
        if r["title"] == title:
            r["status"] = "approved" if decision == "approve" else "rejected"
