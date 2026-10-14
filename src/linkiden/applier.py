"""Applier core. Every application passes guard.check_apply first. Form planning is pure/testable;
live browser steps are isolated in `fill_and_submit` (selectors must be verified on the live sites)."""
from __future__ import annotations
import re
from pathlib import Path
import yaml
from .db import DB
from .guard import check_apply, ApplyBlocked

FIELD_MAP = [  # (regex on label/name/placeholder, contact key)
    (r"full name|^name$|your name", "full_name"), (r"first name", "first_name"), (r"last name|surname", "last_name"),
    (r"e-?mail", "email"), (r"phone|mobile|contact number", "phone"), (r"current ctc|current salary|current compensation", "current_ctc"),
    (r"expected ctc|expected salary|expected compensation", "expected_ctc"), (r"notice", "notice_period"),
    (r"total experience|years of experience", "experience_years"), (r"current location|city", "city"),
    (r"linkedin", "linkedin_url"), (r"github", "github_url"),
]
SENSITIVE = re.compile(r"password|otp|card|cvv|aadhaar|pan\b|bank|ssn|passport|date of birth|dob|gender|religion|caste|marital", re.I)


def load_contact(root: Path) -> dict:
    """Personal form data lives in config/contact.local.yaml (git-ignored)."""
    p = root / "config" / "contact.local.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def plan_form(fields: list[dict], contact: dict) -> tuple[dict, list[dict], list[dict]]:
    """fields: [{'id','label','required','type'}]. Returns (fills, needs_human, refused).
    Sensitive fields are NEVER auto-filled; unknown required fields go to the human via Telegram."""
    fills, needs_human, refused = {}, [], []
    for f in fields:
        label = (f.get("label") or "").strip().lower()
        if f.get("type") == "file":
            fills[f["id"]] = "__RESUME__"; continue
        if SENSITIVE.search(label):
            refused.append(f); continue
        for pat, key in FIELD_MAP:
            if re.search(pat, label) and contact.get(key) not in (None, ""):
                fills[f["id"]] = str(contact[key]); break
        else:
            if f.get("required"):
                needs_human.append(f)
    return fills, needs_human, refused


class Applier:
    def __init__(self, db: DB, settings, gate, contact: dict, root: Path):
        self.db, self.s, self.gate, self.contact, self.root = db, settings, gate, contact, root

    def apply(self, job: dict, resume_text: str, allowed_skills: set[str], page=None, resume_path: str | None = None) -> str:
        try:
            check_apply(self.db, self.s, job, resume_text, allowed_skills)
        except ApplyBlocked as e:
            self.db.set_status(job["id"], "failed", reasons=f"blocked: {e}")
            return f"blocked: {e}"
        if page is None:
            return "dry-run: guard passed, no browser page supplied"
        fields = self.read_fields(page)
        fills, needs_human, refused = plan_form(fields, self.contact)
        if refused or needs_human:
            names = [f.get("label") for f in refused + needs_human]
            if self.gate.ask("form", job["id"] + ":" + ",".join(names), f"{job['title']} @ {job.get('company','')}\nForm needs your input: {names}\nProceed without them / skip?") != "approve":
                self.db.set_status(job["id"], "failed", reasons="form needs human input"); return "skipped: needs human"
        self.fill_and_submit(page, fills, resume_path)
        self.db.set_status(job["id"], "applied")
        return "applied"

    # ---- live browser parts: verify on real sites ----
    def read_fields(self, page) -> list[dict]:
        if page.query_selector("iframe[src*='captcha'], .g-recaptcha, #captcha"):
            raise RuntimeError("CAPTCHA detected: stop and ask human")
        out = []
        for el in page.query_selector_all("input:not([type=hidden]):not([type=submit]), textarea, select"):
            out.append({"id": el.get_attribute("id") or el.get_attribute("name") or "", "label": el.get_attribute("aria-label") or el.get_attribute("placeholder") or el.get_attribute("name") or "",
                        "required": el.get_attribute("required") is not None, "type": el.get_attribute("type") or "text"})
        return out

    def fill_and_submit(self, page, fills: dict, resume_path: str | None):
        for fid, val in fills.items():
            el = page.query_selector(f"#{fid}") or page.query_selector(f"[name='{fid}']")
            if not el: continue
            if val == "__RESUME__":
                if resume_path: el.set_input_files(resume_path)
            else:
                el.fill(val)
            page.wait_for_timeout(400)
        btn = page.query_selector("button[type=submit], input[type=submit]")
        if btn: btn.click()
