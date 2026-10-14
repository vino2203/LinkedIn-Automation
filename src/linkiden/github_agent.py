"""A1 GitHub analyst: read-only repo facts for post topics. Token stays in the header and is never logged."""
from __future__ import annotations
import httpx

def repo_brief(owner: str, repo: str, token: str, client: httpx.Client | None = None) -> dict:
    c = client or httpx.Client(timeout=20)
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "linkiden"}
    meta = c.get(f"https://api.github.com/repos/{owner}/{repo}", headers=h); meta.raise_for_status()
    langs = c.get(f"https://api.github.com/repos/{owner}/{repo}/languages", headers=h).json()
    commits = c.get(f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10", headers=h).json()
    m = meta.json()
    return {"repo": m["full_name"], "description": m.get("description"), "languages": list(langs)[:5], "private": m.get("private", False),
            "recent_commits": [x["commit"]["message"].splitlines()[0] for x in commits if isinstance(x, dict)][:10]}

def post_draft_problems(text: str, allowed: set[str]) -> list[str]:
    """Checks before Gate 3: no secrets, sane length, no unverified tech claims."""
    from .security import _SECRET_RE
    from .tailor import unverified_claims
    issues = []
    if _SECRET_RE.search(text): issues.append("contains secret-like string")
    if len(text) > 3000: issues.append("too long for LinkedIn")
    if len(text) < 200: issues.append("too short")
    bad = unverified_claims(text, allowed)
    if bad: issues.append(f"unverified tech claims: {sorted(bad)}")
    return issues
