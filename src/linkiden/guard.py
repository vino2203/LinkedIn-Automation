"""Apply guard: the single choke point every application must pass. Enforced in code, not prompts."""
from __future__ import annotations
from .db import DB
from .roles import role_status
from .security import url_allowed

class ApplyBlocked(Exception):
    pass

def check_apply(db: DB, settings, job: dict, resume_text: str = "", allowed_skills: set[str] | None = None, extra_domains: set[str] | None = None) -> None:
    """Raises ApplyBlocked with the reason; returns None if the application may proceed."""
    row = db.conn.execute("SELECT status, score FROM jobs WHERE id=?", (job["id"],)).fetchone()
    if not row or row["status"] != "approved":
        raise ApplyBlocked("job not approved at Gate 2")
    if db.approved_before("job", job["id"]) != "approve":
        raise ApplyBlocked("no recorded Gate 2 approval")
    verdict, _ = role_status(job["title"], settings.roles)
    if verdict != "approved":
        raise ApplyBlocked(f"designation not approved ({verdict})")
    if (row["score"] or 0) < settings.min_score:
        raise ApplyBlocked("score below threshold")
    if db.applied_today() >= settings.daily_cap:
        raise ApplyBlocked("daily application cap reached")
    if not url_allowed(job.get("url", ""), extra_domains):
        raise ApplyBlocked("url not on allow-list")
    if resume_text and allowed_skills is not None:
        from .tailor import unverified_claims
        bad = unverified_claims(resume_text, allowed_skills)
        if bad:
            raise ApplyBlocked(f"resume has unverified skills: {sorted(bad)}")
