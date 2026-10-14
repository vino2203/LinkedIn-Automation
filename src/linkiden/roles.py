"""Hard filters: designation allow-list (Gate 1) and location/seniority checks. Pure code, not prompts."""
from __future__ import annotations
import re

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()

# alias -> canonical title in target_roles.yaml
ALIASES = {
    "generative ai engineer": "GenAI Engineer", "gen ai engineer": "GenAI Engineer", "genai developer": "GenAI Engineer",
    "llm engineer": "LLM Application Engineer", "llm developer": "LLM Application Engineer",
    "ai agent engineer": "AI Agent Developer", "agentic ai engineer": "AI Agent Developer", "agentic ai developer": "AI Agent Developer",
    "rag developer": "RAG Engineer", "ai qa engineer": "AI QA Engineer", "llm evaluation engineer": "LLM Evaluation Engineer",
    "sdet ai": "SDET (AI/ML products)",
}

def canonical_role(title: str, roles_cfg: dict) -> str | None:
    """Map a raw job title to a configured role, or None if it matches no configured role."""
    t = _norm(title)
    for r in roles_cfg.get("roles", []):
        if _norm(r["title"]) in t:
            return r["title"]
    for alias, canon in ALIASES.items():
        if alias in t:
            return canon
    return None

def is_excluded(title: str, roles_cfg: dict) -> bool:
    t = _norm(title)
    return any(_norm(x) in t for x in roles_cfg.get("exclude_titles", []))

def role_status(title: str, roles_cfg: dict) -> tuple[str, str | None]:
    """Returns (verdict, canonical): 'excluded' | 'unknown' (-> Gate 1) | 'approved' | 'pending' (-> Gate 1) | 'rejected'."""
    if is_excluded(title, roles_cfg):
        return "excluded", None
    canon = canonical_role(title, roles_cfg)
    if canon is None:
        return "unknown", None
    for r in roles_cfg["roles"]:
        if r["title"] == canon:
            return r.get("status", "pending"), canon
    return "pending", canon  # alias to a title missing in yaml

def location_ok(location: str, prefs: dict) -> bool:
    loc = _norm(location)
    allowed = [_norm(x) for x in prefs.get("locations", [])]
    return not allowed or any(a in loc for a in allowed)
