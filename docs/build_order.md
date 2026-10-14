# Status (2026-10-14)
Built + unit-tested offline (80 tests): config, db, roles, pipeline, Telegram gates, scorer (claude CLI), guard, security, tailor, applier core,
Naukri/Indeed/Instahyre discovery, Gmail parser + mail tracker, GitHub reader, post writer, Composio client, run_daily, run_apply, run_posts, report, schedule.

# Needs the owner at the laptop (blocked on credentials/sessions)
1. config/.env: valid COMPOSIO_API_KEY, own TELEGRAM_CHAT_ID (not the bot id)
2. python scripts/login_portal.py naukri|indeed|instahyre  (manual login)
3. Composio: authorize LinkedIn + Gmail
4. config/contact.local.yaml, approved roles in context/target_roles.yaml, prefs (CTC, notice, cap)
5. Verify portal CSS selectors + Composio tool slugs with --dry-run, then first supervised live run (manual mode)

# Go-live order
run_daily --dry-run -> run_daily -> run_apply --dry-run -> run_apply (1-2 jobs) -> run_posts --dry-run -> run_posts -> install cron (python -m linkiden.schedule)
