"""Instahyre discovery (read-only; saved session via scripts/login_portal.py instahyre).
NOTE: selectors written from memory — VERIFY on the live site. Expect CAPTCHA/bot checks: pacing is slow and we stop on challenge."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote_plus
from .naukri import normalize as _norm

SESSION_DIR = Path(".playwright-session/instahyre")
BASE = "https://www.instahyre.com"
SELECTORS = {"card": "div.employer-block", "title": ".employer-job-name", "company": ".employer-company-name", "location": ".employer-locations", "snippet": ".employer-job-description"}


def search_url(role: str, loc: str) -> str:
    return f"{BASE}/search-jobs/?search={quote_plus(role)}&location={quote_plus(loc)}"


def normalize(raw: dict) -> dict | None:
    j = _norm(raw, base=BASE)
    if j:
        j["source"] = "instahyre"
    return j


def discover(roles: list[str], locations: list[str], max_per_search: int = 15, headless: bool = False) -> list[dict]:
    from playwright.sync_api import sync_playwright
    jobs: list[dict] = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(SESSION_DIR), headless=headless)
        page = ctx.new_page()
        for role in roles:
            for loc in locations:
                page.goto(search_url(role, loc), wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                if page.query_selector("iframe[src*='captcha'], #challenge-form, .g-recaptcha"):
                    ctx.close()
                    raise RuntimeError("instahyre bot-check/CAPTCHA: stopping, ask human")
                for card in page.query_selector_all(SELECTORS["card"])[:max_per_search]:
                    def txt(sel):
                        el = card.query_selector(sel)
                        return el.inner_text() if el else ""
                    a = card.query_selector(SELECTORS["title"])
                    href = a.get_attribute("href") if a else None
                    if href and href.startswith("/"):
                        href = BASE + href
                    j = normalize({"title": txt(SELECTORS["title"]), "company": txt(SELECTORS["company"]),
                                   "location": txt(SELECTORS["location"]), "snippet": txt(SELECTORS["snippet"]), "url": href})
                    if j:
                        jobs.append(j)
        ctx.close()
    return jobs
