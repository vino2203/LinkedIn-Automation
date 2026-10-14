"""SQLite state: jobs pipeline + approvals audit log."""
from __future__ import annotations
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ["found", "scored", "rejected", "awaiting_approval", "approved", "applied", "confirmed", "replied", "failed", "expired"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT, location TEXT, url TEXT, description TEXT,
  score INTEGER, reasons TEXT, status TEXT NOT NULL DEFAULT 'found', resume_path TEXT,
  created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, gate TEXT, subject TEXT, decision TEXT, at TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def job_id(title: str, company: str, location: str) -> str:
    key = "|".join(s.strip().lower() for s in (company, title, location))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


class DB:
    def __init__(self, path: str | Path = "data/jobs.db"):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def add_job(self, source, title, company, location, url, description="") -> tuple[str, bool]:
        """Insert if new (dedupe by company+title+location). Returns (id, created)."""
        jid = job_id(title, company, location)
        if self.conn.execute("SELECT 1 FROM jobs WHERE id=?", (jid,)).fetchone():
            return jid, False
        self.conn.execute(
            "INSERT INTO jobs(id,source,title,company,location,url,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (jid, source, title, company, location, url, description, "found", now(), now()))
        self.conn.commit()
        return jid, True

    def set_status(self, jid: str, status: str, **fields):
        assert status in STATUSES, status
        cols = ["status=?", "updated_at=?"] + [f"{k}=?" for k in fields]
        self.conn.execute(f"UPDATE jobs SET {','.join(cols)} WHERE id=?", [status, now(), *fields.values(), jid])
        self.conn.commit()

    def jobs(self, status: str) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY score DESC", (status,)).fetchall()

    def applied_today(self) -> int:
        day = datetime.now(timezone.utc).date().isoformat()
        return self.conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('applied','confirmed','replied') AND updated_at LIKE ?", (day + "%",)).fetchone()[0]

    def log_approval(self, gate: str, subject: str, decision: str):
        self.conn.execute("INSERT INTO approvals(gate,subject,decision,at) VALUES(?,?,?,?)", (gate, subject, decision, now()))
        self.conn.commit()

    def approved_before(self, gate: str, subject: str) -> str | None:
        r = self.conn.execute("SELECT decision FROM approvals WHERE gate=? AND subject=? ORDER BY id DESC LIMIT 1", (gate, subject)).fetchone()
        return r["decision"] if r else None
