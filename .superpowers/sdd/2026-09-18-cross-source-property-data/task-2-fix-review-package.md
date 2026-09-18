# Task 2 fix review package

Fix base: `933caed`
Fix head: `8c8f55d`

Findings to verify:
- `contact_status` and `contact_scraped_at` survive the normal base normalization path.
- A post-click login prompt is classified as `requires_login`.

Read the Task 2 brief and report, then inspect only this fix range and the focused call sites.
