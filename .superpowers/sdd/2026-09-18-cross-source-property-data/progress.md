# SDD ledger — plan: docs/superpowers/plans/2026-09-18-cross-source-property-data.md

## Pre-flight scan

| Tasks | Shared files/interfaces | Finding | Ruling |
|---|---|---|---|
| 1 ↔ 2 | `src/scrapers/zimmo_scraper.py`; normalized source payload | Task 1 adds public Zimmo fields; Task 2 adds agency/contact fields. Both must preserve existing Zimmo payload keys. | Keep source extraction additive; Task 2 consumes Task 1's normalized keys. |
| 1 ↔ 3 | normalized payload and listing fingerprint | Task 1 emits fields that Task 3 must preserve across rescans. | Task 3 merges only enrichment fields when incoming values are empty. |
| 1 ↔ 4 | shared normalized field names | Task 4 renders only fields defined by Task 1. | UI hides absent values and does not create alternate names. |
| 2 ↔ 3 | `agent_*`, `agency_*`, `contact_*` | Contact extraction can be unavailable on later scans. | Task 3 retains prior non-empty enrichment values. |
| 2 ↔ 4 | `contact_status`, contact fields | UI needs explicit unavailable/login-required states. | Task 2 emits only the four statuses in the plan. |
| 3 ↔ 4 | API listing payload | Persistence must not require a schema migration. | Use existing JSONB payload and existing API pass-through. |
| 4 ↔ 5 | UI and documentation | Final task documents the authenticated setup and verifies the UI. | No live credentials in tests or documentation. |

| Task | Self-consistency scan | Finding | Ruling |
|---|---|---|---|
| 1 | Tests cover three source fixtures and implementation names the same shared fields. | No contradiction. | Proceed. |
| 2 | Fake-driver tests cover click, unavailable, and login-required results matching the declared interface. | No contradiction. | Proceed. |
| 3 | Store tests cover retain and update behavior matching the merge contract. | No contradiction. | Proceed. |
| 4 | Component tests cover non-empty facts and conditional contact actions matching the UI contract. | No contradiction. | Proceed. |
| 5 | Documentation and verification are bounded to safe local/e2e checks. | No contradiction. | Proceed. |

Ruling: implementation remains on the current checkout because the available worktree scripts are Unix-formatted but the Windows shell cannot execute them reliably; the SDD artifact workspace and ledger are still isolated under `.superpowers/sdd/`, and no shared-branch push will be performed.

Task 1: minor (deferred): add explicit assertions for source-created and source-updated dates in the contract fixtures; final review must triage this.
Task 1: complete (commits 9cdf0b4..2b862a2, review clean).
Task 2: fix round 1/5 (2 addressed, 0 open; commits 933caed..8c8f55d).
Task 2: complete (commits 2b862a2..8c8f55d, review clean).
Task 3: fix round 1/5 (1 addressed, 0 open; commits 67bdd52..cdeabbc).
Task 3: complete (commits 8c8f55d..cdeabbc, review clean).
Task 4: fix round 1/5 (2 addressed, 0 open; commits 3af4aee..0f5e192).
Task 4: minor (deferred): strengthen invalid-date assertions to check each omitted label independently; final review must triage this.
Task 4: complete (commits cdeabbc..0f5e192, review clean).
Task 5: minor (deferred): clarify that the smoke test uses a local Postgres test service but no live portal service or credentials; final review must triage this.
Task 5: complete (commits 0f5e192..2ffec86, review clean).
