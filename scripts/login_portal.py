"""One-time manual login. Opens a visible browser; YOU type credentials/OTP. Session is saved locally; the agent never sees your password.
Usage: python scripts/login_portal.py naukri|indeed|instahyre|linkedin"""
import sys
from playwright.sync_api import sync_playwright

URLS = {"naukri": "https://www.naukri.com/nlogin/login", "indeed": "https://secure.indeed.com/auth",
        "instahyre": "https://www.instahyre.com/login/", "linkedin": "https://www.linkedin.com/login"}
name = sys.argv[1]
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(f".playwright-session/{name}", headless=False)
    ctx.new_page().goto(URLS[name])
    input(f"Log in to {name} in the browser, then press Enter here to save the session...")
    ctx.close()
