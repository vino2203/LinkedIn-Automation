"""Gmail parsing: OTP extraction and application-confirmation detection. Only trusted portal senders are ever read."""
from __future__ import annotations
import re

TRUSTED_SENDERS = {"naukri.com", "indeed.com", "instahyre.com", "linkedin.com", "greenhouse.io", "lever.co", "myworkdayjobs.com", "workable.com"}
_OTP = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")
_OTP_CTX = re.compile(r"(otp|verification code|one[- ]time|security code|passcode)", re.I)
_CONFIRM = re.compile(r"(thank you for applying|application (has been )?(received|submitted)|successfully applied|we received your application)", re.I)
_REPLY = re.compile(r"(interview|schedule a call|shortlisted|next steps|would like to connect)", re.I)

def sender_domain(sender: str) -> str:
    m = re.search(r"@([A-Za-z0-9.\-]+)", sender or "")
    return m.group(1).lower() if m else ""

def sender_trusted(sender: str) -> bool:
    d = sender_domain(sender)
    return any(d == t or d.endswith("." + t) for t in TRUSTED_SENDERS)

def extract_otp(sender: str, subject: str, body: str) -> str | None:
    """Return an OTP only from trusted senders and only when OTP context words are present."""
    if not sender_trusted(sender):
        return None
    text = f"{subject}\n{body}"
    if not _OTP_CTX.search(text):
        return None
    for m in _OTP.finditer(text):
        code = m.group(1)
        if not (1990 <= int(code) <= 2100 and len(code) == 4):  # skip years
            return code
    return None

def classify(sender: str, subject: str, body: str) -> str:
    if not sender_trusted(sender):
        return "ignore"
    text = f"{subject}\n{body}"
    if _CONFIRM.search(text):
        return "confirmation"
    if _REPLY.search(text):
        return "recruiter_reply"
    return "other"
