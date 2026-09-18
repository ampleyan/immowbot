# Task 5: End-to-end verification and operational handoff

Complete the documentation and final verification slice for the cross-source enrichment work. Read the full plan only if needed: `docs/superpowers/plans/2026-09-18-cross-source-property-data.md`.

Files:
- Modify `README.md` or the most relevant existing scraper/Docker documentation file; choose one existing documentation file and keep the change focused.
- Modify `tests/test_e2e_smoke.py` only if an existing safe smoke test can verify the normalized fields without live credentials; otherwise do not change it.

Documentation must explain:
- Public fields are scraped without login.
- Zimmo contact actions use only visible `Bellen`/`Mailen` browser controls.
- `contact_status` values are `available`, `unavailable`, `requires_login`, or `reveal_failed`.
- Cookies, JWTs, refresh tokens, and passwords must never be committed or placed in Docker images/logs.
- Local authenticated-browser setup, if needed, uses a persistent local profile or runtime-mounted secret outside the repository; do not include actual credentials or cookie examples.
- Existing `NEW TO CHECK` means first seen within 24 hours and still unreviewed.

Run the full applicable checks in the repository: focused and available Python tests, frontend type-check, unit tests, build, and `git diff --check`. Separate environment-only failures such as missing `psycopg`, Windows encoding/Ollama, existing ESLint baseline errors, or unavailable live services from regressions. Do not push.

Write the report to `.superpowers/sdd/2026-09-18-cross-source-property-data/task-5-report.md`, commit with `docs: document source enrichment and contact safety`, and return only status, commit, one-line tests, and concerns.
