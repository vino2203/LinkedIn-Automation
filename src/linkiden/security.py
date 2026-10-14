"""Security helpers: secret redaction, untrusted-text sanitising, URL allow-list, .env permission check."""
from __future__ import annotations
import logging
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlparse

SECRET_PATTERNS = [
    r"github_pat_[A-Za-z0-9_]{20,}", r"ghp_[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9_\-]{10,}", r"sk-[A-Za-z0-9]{20,}",
    r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b",          # telegram bot token
    r"\bck_[A-Za-z0-9]{10,}\b", r"\bak_[A-Za-z0-9]{10,}\b",  # composio
    r"AKIA[0-9A-Z]{16}",
]
_SECRET_RE = re.compile("|".join(SECRET_PATTERNS))

def redact(text: str) -> str:
    return _SECRET_RE.sub("[REDACTED]", text)

class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.getMessage())); record.args = ()
        return True

def install_log_redaction() -> None:
    for h in logging.getLogger().handlers or [logging.StreamHandler()]:
        h.addFilter(RedactingFilter())

# --- prompt-injection hygiene for untrusted job text -------------------------------------------
_INJECTION = re.compile(r"(ignore (all |any )?(previous|prior|above) instructions|disregard .{0,30}instructions|you are now|system prompt|"
                        r"reveal .{0,30}(key|token|password|secret)|send .{0,40}(resume|email|otp)|<\s*/?\s*(system|assistant)\s*>)", re.I)

def sanitize_untrusted(text: str, max_len: int = 6000) -> tuple[str, bool]:
    """Strip control chars, neutralise injection phrases, cap length. Returns (clean, flagged)."""
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text or "")[:max_len]
    flagged = bool(_INJECTION.search(text))
    return _INJECTION.sub("[removed]", text), flagged

# --- URL allow-list for the applier ------------------------------------------------------------
PORTAL_DOMAINS = {"naukri.com", "indeed.com", "instahyre.com", "linkedin.com"}
ATS_DOMAINS = {"greenhouse.io", "lever.co", "myworkdayjobs.com", "workable.com", "ashbyhq.com", "smartrecruiters.com", "icims.com", "zohorecruit.com"}

def url_allowed(url: str, extra: set[str] | None = None) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return False
    host = u.hostname.lower()
    return any(host == d or host.endswith("." + d) for d in PORTAL_DOMAINS | ATS_DOMAINS | (extra or set()))

# --- file permissions --------------------------------------------------------------------------
def env_permissions_ok(path: Path) -> bool:
    mode = stat.S_IMODE(os.stat(path).st_mode)
    return mode & (stat.S_IRWXG | stat.S_IRWXO) == 0

def scan_for_secrets(root: Path, skip=(".venv", ".git", "config/.env", "__pycache__", ".playwright-session", "tests")) -> list[str]:
    hits = []
    for p in root.rglob("*"):
        rel = str(p.relative_to(root))
        if not p.is_file() or any(s in rel for s in skip) or p.suffix in {".pdf", ".db", ".png", ".mp4", ".faiss", ".pkl"}:
            continue
        try:
            if _SECRET_RE.search(p.read_text(errors="ignore")):
                hits.append(rel)
        except OSError:
            pass
    return hits
