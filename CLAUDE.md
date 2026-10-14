# Global rules (all agents)

1. NEVER apply to a job, send a message, or publish a post without an explicit approval recorded in data/approvals_log.md (Hermes gates).
2. NEVER invent skills, employers, dates, or metrics. Only claim what is in context/resume.md or context/skills_evidence.md.
3. Only pursue designations listed (approved) in context/target_roles.yaml. Unknown titles -> Gate 1 (ask the user).
4. Apply only if match score >= prefs.min_match_score AND the role passes the hard filters in prefs.yaml.
5. Never ask for, store, or log passwords. Use OAuth (Composio) or a saved browser session. Secrets live only in config/.env.
6. Respect daily caps and human-like pacing (prefs.max_applications_per_day). Stop on CAPTCHA/assessment and ask via Hermes.
7. Gmail: read-only, job-related senders only. OTP = latest message from that portal's sender only.
8. Log every action to data/ and logs/. Dedupe jobs by company+title+location before scoring.
9. Context load order: CLAUDE.md -> context/profile.md -> context/target_roles.yaml -> context/prefs.yaml -> the agent's own spec in agents/.
