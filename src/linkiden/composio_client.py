"""Thin Composio REST client (LinkedIn post, Gmail fetch). Endpoint/slug names follow Composio v3 docs from memory — VERIFY with a dry call.
Publishing is impossible without a recorded Gate 3 approval."""
from __future__ import annotations
import httpx
from .db import DB

BASE = "https://backend.composio.dev/api/v3"

class PublishBlocked(Exception):
    pass

class Composio:
    def __init__(self, api_key: str, user_id: str = "default", client: httpx.Client | None = None):
        self.h = {"x-api-key": api_key, "Content-Type": "application/json"}; self.user_id = user_id; self.http = client or httpx.Client(timeout=60)

    def execute(self, slug: str, arguments: dict) -> dict:
        r = self.http.post(f"{BASE}/tools/execute/{slug}", headers=self.h, json={"user_id": self.user_id, "arguments": arguments})
        r.raise_for_status(); return r.json()

    def whoami_linkedin(self) -> dict:
        return self.execute("LINKEDIN_GET_MY_INFO", {})

    def post_linkedin(self, db: DB, topic_key: str, text: str, author_urn: str | None = None) -> dict:
        if db.approved_before("post", topic_key) != "approve":
            raise PublishBlocked("no Gate 3 approval recorded")
        args = {"commentary": text, "visibility": "PUBLIC"}
        if author_urn: args["author"] = author_urn
        return self.execute("LINKEDIN_CREATE_LINKED_IN_POST", args)

    def fetch_gmail(self, query: str = "newer_than:2d", max_results: int = 20) -> list[dict]:
        res = self.execute("GMAIL_FETCH_EMAILS", {"query": query, "max_results": max_results})
        items = (res.get("data") or {}).get("messages", []) if isinstance(res, dict) else []
        return [{"sender": m.get("sender", ""), "subject": m.get("subject", ""), "body": m.get("messageText", m.get("preview", ""))} for m in items]
