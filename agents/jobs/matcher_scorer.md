# Matcher/Scorer

**Role:** Scores each job vs resume + skills_evidence.
**Inputs:** jobs.db, resume.md, prefs.yaml
**Outputs:** score + reasons; keep if >= min_match_score and role approved
**Rules:** Unknown role -> Gate 1.
