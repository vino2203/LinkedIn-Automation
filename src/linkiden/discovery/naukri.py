"""Naukri discovery (read-only). Uses a saved logged-in browser session (scripts/login_portal.py naukri).
NOTE: CSS selectors below were written from memory of Naukri's markup and MUST be verified against the live site."""
from __future__ import annotations
import re
from pathlib import Path

SESSION_DIR = Path(".playwright-session/naukri")
SELECTORS = {  # verify in browser devtools
    "card": "div.srp-jobtuple-wrapper",
    "title": "a.title", "company": "a.comp-name", "location": "span.locWdth", "snippet": "span.job-desc",
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def search_url(role: str, location: str) -> str:
    return f"https://www.naukri.com/{slugify(role)}-jobs-in-{slugify(location)}"


def normalize(raw: dict, base="https://www.naukri.com") -> dict | None:
    """Raw card fields -> job dict. Returns None if essential fields are missing."""
    title, company = (raw.get("title") or "").strip(), (raw.get("company") or "").strip()
    if not title or not company:
        return None
    return {"source": "naukri", "title": title, "company": company, "location": (raw.get("location") or "").strip(),
            "url": raw.get("url") or base, "description": (raw.get("snippet") or "").strip()}


def discover(roles: list[str], locations: list[str], max_per_search: int = 20, headless: bool = True) -> list[dict]:
    from playwright.sync_api import sync_playwright
    jobs: list[dict] = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(SESSION_DIR), headless=headless)
        page = ctx.new_page()
        for role in roles:
            for loc in locations:
                page.goto(search_url(role, loc), wait_until="domcontentloaded")
                page.wait_for_timeout(2500)  # human-like pacing
                for card in page.query_selector_all(SELECTORS["card"])[:max_per_search]:
                    def txt(sel):
                        el = card.query_selector(sel); return el.inner_text() if el else ""
                    link = card.query_selector(SELECTORS["title"])
                    job = normalize({"title": txt(SELECTORS["title"]), "company": txt(SELECTORS["company"]),
                                     "location": txt(SELECTORS["location"]), "snippet": txt(SELECTORS["snippet"]),
                                     "url": link.get_attribute("href") if link else None})
                    if job:
                        jobs.append(job)
        ctx.close()
    return jobs
