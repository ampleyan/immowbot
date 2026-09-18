# Task 2: Zimmo agency and contact enrichment

Implement the Zimmo-only agency and visible contact enrichment slice after Task 1. Read the full plan only if needed: `docs/superpowers/plans/2026-09-18-cross-source-property-data.md`.

Files:
- Modify `src/scrapers/zimmo_scraper.py`.
- Add or modify `tests/test_zimmo_scraper.py`.
- Modify `src/scraper_manager.py` only if an authenticated persistent browser profile must be configured centrally; avoid this unless required by the existing architecture.

Interfaces:
- Add `_reveal_contact_details(driver)` returning `agent_phone`, `agent_email`, `contact_status`, and `contact_scraped_at`.
- Add agency extraction returning `agency_name`, `agency_address`, and `agency_url` from structured data or visible provider markup.
- `contact_status` is one of `available`, `unavailable`, `requires_login`, or `reveal_failed`.

Requirements:
- Public agency extraction works without login.
- Click only visible Zimmo `Bellen`/`Mailen` controls with Selenium; never call undocumented endpoints directly and never bypass authentication barriers.
- A failed or unavailable contact reveal must not fail the property scrape.
- Tests must cover successful click/extraction, no contact controls, and login-required state using fake drivers/HTML.
- Do not add credentials or cookies to code, fixtures, logs, or configuration.
- Run `python -m unittest tests.test_zimmo_scraper -v`, `python -m compileall -q src`, and `git diff --check`.
- Commit with `feat: enrich Zimmo agency and contacts`.

Write the complete report to `.superpowers/sdd/2026-09-18-cross-source-property-data/task-2-report.md`. Return only status, commit, one-line test summary, and concerns. Do not push.
