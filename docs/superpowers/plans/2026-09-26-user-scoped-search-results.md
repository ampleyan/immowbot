# User-scoped Searches and Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure each signed-in user can view and manage only listings and runs observed by their own searches.

**Architecture:** Keep the shared property catalog, and add a run-to-listing-version association so identical listing observations can belong to multiple users' runs. Add SQL-scoped store queries and per-user exclusions, route every API result operation through those queries, and key background job state by user ID.

**Tech Stack:** Python 3.12, FastAPI, psycopg 3, PostgreSQL migrations, unittest, Vue 3.

**Spec:** `docs/superpowers/specs/2026-09-26-user-scoped-search-results-design.md`

## Global Constraints

- Preserve existing users, searches, runs, listings, and versions; do not drop, truncate, or rewrite them.
- Backfill run-to-listing observations from existing `listing_versions.run_id` values; grant versions whose search owner has no matching user account to the lowest-ID admin, without changing credentials.
- Keep canonical property identity and payload versions shared.
- Store ownership must be enforced in SQL predicates, not only by filtering global results in application code.
- Keep endpoint URLs, response shapes, and the existing one-home-search-per-user UI behavior.
- Return not found for another user's run or an unobserved listing without revealing whether the identifier exists.
- Run tests and build the Docker image without starting or recreating PostgreSQL.

## Review Focus

- Two users observe an identical listing: both must have an observation link even though the payload version is globally deduplicated.
- A user requests another user's run or listing ID: detail, history, selection, and mutations must behave as not found.
- Removing or merging a listing must not delete or rewrite shared catalog data used by another user's run.
- Two users collect concurrently: progress, cancellation, and translation status must remain scoped to the initiating user.
- Migration backfill and rollback-on-failure must preserve all existing rows and recorded run ownership; assign versions with missing search-owner accounts only to the lowest-ID admin, and fail transactionally if no admin exists.

---

### Task 1: Persist and query per-run listing observations

**Files:**
- Create: `migrations/003_user_scoped_results.sql`
- Modify: `src/buyer/property_store.py`
- Test: `tests/test_property_store.py`
- Test: `tests/test_user_scoped_migration.py`

**Interfaces:**
- Consumes: existing `runs`, `searches`, `listings`, and `listing_versions` tables.
- Produces: `PropertyStore.user_listings(user_id, transaction_type)`, `PropertyStore.get_run_for_user(user_id, run_id)`, `PropertyStore.listings_for_user_run(user_id, run_id)`, `PropertyStore.listing_history_for_user(user_id, source, source_listing_id)`, `PropertyStore.listing_visible_to_user(user_id, source, source_listing_id)`, and `PropertyStore.exclude_user_listing(user_id, source, source_listing_id)`.

- [ ] **Step 1: Write store tests for shared observations and scoped reads**

Add tests where two users' searches observe the same unchanged listing and distinct listings. Assert each user's scoped results contain only their observations, each user's run detail and history exclude the other's rows, and the existing global `latest_listings()` behavior remains available to internal shared-catalog callers.

- [ ] **Step 2: Run the new store tests to confirm they fail**

Run: `python -m unittest tests.test_property_store`
Expected: the new scoped method tests fail because the methods and observation table are absent.

- [ ] **Step 3: Add the migration and backfill test**

Create `run_listing_observations` linking `run_id`, `listing_id`, and `listing_version_id`, keyed by `(run_id, listing_id)`, plus `legacy_user_listing_versions` keyed by `(user_id, listing_id, listing_version_id)` and `user_listing_exclusions` keyed by `(user_id, listing_id)`. Backfill run associations from existing version/run links, using the newest version where a run has multiple versions for one listing. Grant versions whose run's search references no existing user row to the lowest-ID admin through `legacy_user_listing_versions`. Add migration tests with valid run/version FKs but a missing search owner account, and verify admin-only grants, no-admin rollback, unchanged admin credentials, and unchanged original row counts and values. Do not relax the `listing_versions.run_id` constraint in tests.

- [ ] **Step 4: Record observations even when a payload version already exists**

Update `save_listing(run_id, listing)` to resolve the owning user, shared listing, and payload-version IDs, then upsert the run association and clear that owner's exclusion in the same transaction. A repeated observation in a second run must associate to the existing version without adding a duplicate content version.

- [ ] **Step 5: Implement the user-scoped store methods**

Use joins from observations to runs and searches with `searches.user_id = %s`, unioned with the user's legacy version grants. Resolve the newest visible version and compute first/last observed times and price history from that user's own observations. Exclude the user's hidden listings. Add run ownership, listing visibility, and exclusion operations with SQL ownership predicates.

- [ ] **Step 6: Run store and migration tests**

Run: `python -m unittest tests.test_property_store tests.test_user_scoped_migration`
Expected: all tests pass; the migration test confirms legacy rows remain unchanged.

- [ ] **Step 7: Commit the store and migration changes**

```bash
git add migrations/003_user_scoped_results.sql src/buyer/property_store.py tests/test_property_store.py tests/test_user_scoped_migration.py
git commit -m "feat: associate listing results with user runs"
```

### Task 2: Scope result APIs and shared-catalog mutations

**Files:**
- Modify: `src/buyer/api.py`
- Test: `tests/test_api_database_integration.py`
- Test: `tests/test_user_scoped_api.py`

**Interfaces:**
- Consumes: Task 1's `user_listings`, `listings_for_user_run`, `listing_history_for_user`, `listing_visible_to_user`, and `exclude_user_listing` methods.
- Produces: Existing API endpoints with unchanged URLs and response fields, scoped to the authenticated user's run observations.

- [ ] **Step 1: Add two-user API integration tests**

Test the main feed, batch lookup, run list/detail, alerts, duplicates, smart-list items, exports, saved-list items, change history, deletion, duplicate actions, and selected-run input with two users who share one listing and have different listings. Assert responses and accepted IDs are limited to each user's visible results, another user's run/listing requests return 404, and a user's removal or duplicate operation leaves shared rows intact for the other user.

- [ ] **Step 2: Run the new API tests to confirm they fail**

Run: `python -m unittest tests.test_user_scoped_api`
Expected: tests expose global result queries and missing run/listing ownership checks.

- [ ] **Step 3: Route API reads and selected actions through the scoped store methods**

Replace global latest-listing reads in user-facing endpoints with `user_listings(user_id, type)`. Use `listings_for_user_run(user_id, run_id)` and `listing_history_for_user(...)` for detail/history. Validate all client-supplied listing identifiers before batch, selected-run, translation, and similar actions.

- [ ] **Step 4: Make removal and duplicate actions safe for shared rows**

Change ordinary listing removal to create a user exclusion. Clear it when that user observes the listing in a subsequent run. Remove shared row deletion/rewrites from regular-user duplicate merge handling and ensure inaccessible IDs return 404.

- [ ] **Step 5: Run API and related store tests**

Run: `python -m unittest tests.test_user_scoped_api tests.test_api_database_integration tests.test_property_store`
Expected: both-user result isolation passes and existing response shapes remain unchanged.

- [ ] **Step 6: Commit the API changes**

```bash
git add src/buyer/api.py tests/test_api_database_integration.py tests/test_user_scoped_api.py
git commit -m "fix: scope listing APIs to the signed-in user"
```

### Task 3: Isolate background collection and translation state

**Files:**
- Modify: `src/buyer/api.py`
- Test: `tests/test_user_scoped_api.py`
- Test: `tests/test_user_jobs.py`

**Interfaces:**
- Consumes: authenticated user IDs and Task 1's scoped listing query.
- Produces: `collection_jobs[user_id]` and `translation_jobs[user_id]` state used by run start/cancel, progress stream, and translation routes.

- [ ] **Step 1: Add job-state tests for concurrent users**

Test that each user's progress stream reports only their job, cancellation affects only their job, each user is limited to one active collection, and two different users can have active collections simultaneously.

- [ ] **Step 2: Run the job-state tests to confirm they fail**

Run: `python -m unittest tests.test_user_jobs`
Expected: current process-global job state causes cross-user status and cancellation failures.

- [ ] **Step 3: Key collection state and controls by user ID**

Store collection threads, cancellation events, progress queues, and snapshots under the authenticated user ID. Update start, stream, active-cancel, and active-run checks to read only that user's state.

- [ ] **Step 4: Key translation state and queues by user ID**

Build stale and selected translation work from the requesting user's visible results. Keep translation writes as shared listing enrichment, but report progress only to the initiating user.

- [ ] **Step 5: Run job-state and API tests**

Run: `python -m unittest tests.test_user_jobs tests.test_user_scoped_api`
Expected: per-user progress, cancellation, and concurrent collection assertions pass.

- [ ] **Step 6: Commit the job-state changes**

```bash
git add src/buyer/api.py tests/test_user_jobs.py tests/test_user_scoped_api.py
git commit -m "fix: isolate background jobs by user"
```

### Task 4: Run regression checks and build the image

**Files:**
- No product files; use the test and build commands below.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: verified migration, API behavior, and Docker image build.

- [ ] **Step 1: Run the complete Python test suite**

Run: `python -m unittest discover -s tests`
Expected: all runnable tests pass; PostgreSQL-dependent tests may skip only when their configured test database is unavailable.

- [ ] **Step 2: Build the Docker image without starting services**

Run: `docker compose build app`
Expected: build completes successfully. Do not run `docker compose down`, remove volumes, or recreate PostgreSQL.

- [ ] **Step 3: Commit any regression fixes with their owning task**

Include any necessary correction in the matching task commit and rerun its test command before handoff.
