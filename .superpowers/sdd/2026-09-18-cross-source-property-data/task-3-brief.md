# Task 3: Preserve enriched data across rescans

Implement the persistence slice for source enrichment. Read the full plan only if needed: `docs/superpowers/plans/2026-09-18-cross-source-property-data.md`.

Files:
- Modify `src/buyer/property_store.py` in `save_listing`.
- Modify `tests/test_property_store.py`.
- Modify `src/buyer/api.py` only if API serialization needs explicit contact/source fields; avoid this unless tests prove pass-through is insufficient.

Requirements:
- A rescan with missing contact/agency/source-enrichment values must not erase a previously captured non-empty value.
- A later non-empty value replaces an empty value.
- Preserve existing listing history behavior and do not create a migration.
- Do not merge ordinary listing fields; merge only enrichment keys: `agent_name`, `agent_phone`, `agent_email`, `agency_name`, `agency_address`, `agency_url`, `source_created_at`, `source_updated_at`, `contact_status`, and `contact_scraped_at`.
- Do not create a new listing version when the normalized fingerprint is otherwise unchanged.
- Preserve the existing rule that description translation differences do not create meaningful listing changes.
- Add tests that save a listing with contacts, rescan without contacts, and assert retention; then save a later non-empty value and assert update.
- Do not add credentials/cookies, inline comments, or Python type annotations.
- Run the focused property-store tests, `python -m compileall -q src`, and `git diff --check`.
- Commit with `fix: preserve source enrichment during rescans`.

Write the full report to `.superpowers/sdd/2026-09-18-cross-source-property-data/task-3-report.md`. Return only status, commit, one-line tests, and concerns. Do not push.
