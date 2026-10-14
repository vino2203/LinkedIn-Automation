"""Prints crontab lines from config/schedule.yaml (does not install anything)."""
from __future__ import annotations
import yaml
from .config import ROOT

def cron_lines(cfg: dict, root=ROOT) -> list[str]:
    py = f"{root}/.venv/bin/python"; pre = f"cd {root} && {py} -m linkiden"
    def hm(t): h, m = t.split(":"); return int(m), int(h)
    out = []
    for key, mod in [("job_discovery", "run_daily"), ("linkedin_posts", "run_posts")]:
        m, h = hm(cfg[key]["time"]); every = cfg[key]["every_days"]
        out.append(f"{m} {h} {'*' if every == 1 else f'*/{every}'} * * {pre}.{mod} >> logs/{mod}.log 2>&1")
    m, h = hm(cfg["daily_report"]["time"]); out.append(f"{m} {h} * * * {pre}.report >> logs/report.log 2>&1")
    return out

if __name__ == "__main__":
    print("\n".join(cron_lines(yaml.safe_load((ROOT / "config/schedule.yaml").read_text()))))
