# Task 1: Normalize high-value public fields

Read the full plan at `docs/superpowers/plans/2026-09-18-cross-source-property-data.md` only if a requirement below is ambiguous. This task is the first implementation slice: add a shared normalized property-data contract for useful public fields from Immoweb, Immoscoop, and Zimmo without removing existing source-specific details.

Files:
- Modify `src/base_scraper.py` in `_normalize_property_data`.
- Modify `src/scrapers/immoweb_scraper.py` detail extraction.
- Modify `src/scrapers/immoscoop_scraper.py` structured detail extraction.
- Modify `src/scrapers/zimmo_scraper.py` `ng-state` and HTML extraction.
- Add `tests/test_source_data_contract.py`.

Shared keys: `source_created_at`, `source_updated_at`, `agent_name`, `agent_phone`, `agent_email`, `agency_name`, `agency_address`, `agency_url`, `bathrooms`, `floor`, `epc_value`, `epc_certificate_number`, `heating_type`, `renovation_obligation`, `renovation_year`, `monthly_charges`, `cadastral_income`, `parking`, `terrace`, `garden`, `solar_panels`, `investment_property`, `new_build`, `p_score`, and `g_score`.

Requirements:
- Missing source values must stay empty/None; never guess.
- Preserve existing `all_property_details`, `property_details`, and category dictionaries.
- Use fixture-based tests for one representative payload from each source.
- Do not add credentials, cookies, inline comments, or Python type annotations.
- Do not create a database migration.
- Run `python -m unittest tests.test_source_data_contract -v`, `python -m compileall -q src`, and `git diff --check`.
- Commit with `feat: normalize cross-source property facts`.

Write the complete implementation report to `.superpowers/sdd/2026-09-18-cross-source-property-data/task-1-report.md`, including changed files, commit hash, tests and output, self-review, and concerns. Return only status, commit, one-line test summary, and concerns.
