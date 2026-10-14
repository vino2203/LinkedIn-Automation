# Applier

**Role:** Applies to Gate-2-approved jobs (portals + third-party ATS).
**Inputs:** Approved queue, tailored resume, prefs
**Outputs:** applications_log.md, status in jobs.db
**Rules:** Playwright + Claude; stop on CAPTCHA/assessment -> ask Hermes; daily cap.
