"""Load secrets (config/.env) and context (context/*.yaml). Never prints secret values."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SECRETS = ["COMPOSIO_API_KEY", "GITHUB_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]


@dataclass
class Settings:
    secrets: dict
    prefs: dict
    roles: dict

    def secret(self, name: str) -> str:
        value = self.secrets.get(name) or os.environ.get(name, "")
        if not value:
            raise KeyError(f"{name} is not set in config/.env")
        return value.strip()

    def missing_secrets(self) -> list[str]:
        return [k for k in REQUIRED_SECRETS if not (self.secrets.get(k) or "").strip()]

    @property
    def min_score(self) -> int:
        return int(self.prefs.get("min_match_score", 90))

    @property
    def daily_cap(self) -> int:
        return int(self.prefs.get("max_applications_per_day", 15))


def load_settings(root: Path = ROOT) -> Settings:
    secrets = {k: (v or "").strip() for k, v in dotenv_values(root / "config" / ".env").items()}
    prefs = yaml.safe_load((root / "context" / "prefs.yaml").read_text()) or {}
    roles = yaml.safe_load((root / "context" / "target_roles.yaml").read_text()) or {}
    return Settings(secrets, prefs, roles)
