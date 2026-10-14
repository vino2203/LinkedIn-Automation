"""Human-in-the-loop gate over Telegram (Gate 1 designation, Gate 2 job, Gate 3 post). Nothing proceeds without a recorded Approve."""
from __future__ import annotations
import hashlib
import time
import httpx
from .db import DB

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramGate:
    def __init__(self, token: str, chat_id: str, db: DB, timeout_hours: float = 24):
        self.token, self.chat_id, self.db = token, str(chat_id), db
        self.timeout = timeout_hours * 3600
        self.http = httpx.Client(timeout=40)
        self._offset = 0

    def _call(self, method: str, **payload):
        r = self.http.post(API.format(token=self.token, method=method), json=payload)
        r.raise_for_status()
        return r.json()["result"]

    def ask(self, gate: str, subject: str, text: str, wait: bool = True) -> str:
        """Send an Approve/Reject card. Returns 'approve' | 'reject' | 'expired'. Remembers earlier decisions per (gate, subject)."""
        prior = self.db.approved_before(gate, subject)
        if prior in ("approve", "reject") and gate == "designation":
            return prior
        key = f"{gate}:{hashlib.sha1(subject.encode()).hexdigest()[:8]}"
        self._call("sendMessage", chat_id=self.chat_id, text=text, reply_markup={"inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"{key}:approve"}, {"text": "❌ Reject", "callback_data": f"{key}:reject"}]]})
        if not wait:
            return "sent"
        decision = self._wait(key)
        self.db.log_approval(gate, subject, decision)
        return decision

    def _wait(self, key: str) -> str:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            for u in self._call("getUpdates", offset=self._offset, timeout=30, allowed_updates=["callback_query"]):
                self._offset = u["update_id"] + 1
                cq = u.get("callback_query")
                if cq and str(cq["message"]["chat"]["id"]) == self.chat_id and cq["data"].startswith(key + ":"):
                    self._call("answerCallbackQuery", callback_query_id=cq["id"], text="Recorded")
                    return cq["data"].rsplit(":", 1)[1]
        return "expired"

    def notify(self, text: str):
        self._call("sendMessage", chat_id=self.chat_id, text=text)


def job_card(job: dict) -> str:
    return (f"Job: {job['title']} @ {job['company']}\nLocation: {job['location']}\nScore: {job['score']}%\n"
            f"Why: {job.get('reasons','')}\n{job['url']}")
