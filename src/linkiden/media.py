"""Screenshots / demo recordings for posts (Playwright). Live-only; verify against your running demo."""
from __future__ import annotations
from pathlib import Path
from .security import url_allowed

def _safe_target(url: str) -> bool:
    return url.startswith("http://localhost") or url.startswith("http://127.0.0.1") or url_allowed(url, {"github.com", "streamlit.app", "huggingface.co"})

def capture(url: str, out_dir: Path, name: str, record_video: bool = False) -> dict:
    """Open a demo URL (local app or allow-listed host), take a screenshot, optionally record a short video."""
    if not _safe_target(url):
        raise ValueError("demo url not allowed")
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(out_dir / "video") if record_video else None)
        page = ctx.new_page(); page.goto(url, wait_until="networkidle"); page.wait_for_timeout(3000)
        img = out_dir / f"{name}.png"; page.screenshot(path=str(img))
        ctx.close(); b.close()
    vids = sorted((out_dir / "video").glob("*.webm")) if record_video else []
    return {"image": str(img), "video": str(vids[-1]) if vids else None}
