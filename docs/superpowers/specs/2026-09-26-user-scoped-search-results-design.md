# User-scoped searches and results

## Goal

Give each signed-in account independent search results and run history. A user must not see, select, change, or delete another user's collected results, even when both users encounter the same property. Preserve existing PostgreSQL data and avoid duplicating the canonical property catalog.

## Current behavior

- Search configurations and runs are already linked to a user through `searches.user_id` and `runs.search_id`.
- Property rows and versions are global. `latest_listings()` returns the globally newest version, and the API uses it for dashboards, duplicates, alerts, smart lists, exports, selected runs, and translation queues.
- `listing_versions` has a global uniqueness constraint on `(listing_id, content_hash)`. An unchanged observation by a second user's run does not create a version row associated with that run.
- The API's collection and translation progress state is process-global. Run-listing and listing-history endpoints authenticate the caller but do not verify ownership of the requested run or property.
- The listing deletion endpoint deletes from the shared catalog.

## Design

Keep canonical listing identity and deduplicated payload versions shared. Add a migration that records each run's observation of a listing and the version seen by that run. Every successful scrape must create this association, including when the payload hash already exists. This lets the application reuse property data while resolving a user's visible payload and history only from runs owned by that user.

Add user-scoped store queries for current listings, run listings, and listing history. They resolve ownership through `runs -> searches.user_id`, choose the newest version observed by that user's runs, and derive user-facing observation dates and price history from those runs. Update API paths that return or act on results—including the main listing feed, batch lookup, selected runs, run detail, duplicates, alerts, smart lists, exports, saved-list details, changes, and translation selection—to use those scoped queries. Listing IDs supplied by a client must be checked against that user's visible results before use.

Make removal from the feed a per-user exclusion rather than deleting the shared property row. Clear that exclusion when the user collects the property again. Duplicate merging must not delete or rewrite shared catalog rows from an ordinary user's request; keep shared catalog maintenance separate from per-user duplicate handling. This preserves other users' data and keeps the existing shared catalog intact.

Key collection and translation progress by user ID. A user's stream and cancellation request must read or change only that user's job. Keep the existing limit of one active collection per user; allow different users to collect concurrently. The stale-translation queue must also be built from the requesting user's results. Translation remains shared listing enrichment, not personal search data.

## Existing data and migration

- Do not drop, truncate, or rewrite existing users, searches, runs, listings, or versions.
- Backfill the new run-to-listing association from existing `listing_versions.run_id` values. Historical observations already represented by a version/run link remain visible to that run's owner. Store legacy grants in `legacy_user_listing_versions`. For legacy listings with no recorded run link, grant the listing and its versions to the lowest-ID user with `is_admin = TRUE`; keep the listing and versions in the existing shared catalog. Do not change that account's credentials. If no admin exists, the migration must fail without modifying existing data.
- Existing searches retain their current `user_id`; no account reassignment is performed.
- A user-specific exclusion table starts empty, so no existing properties are hidden.
- Keep the global listing/content uniqueness constraint and add association records for repeated observations. Existing property notes, workflows, lists, alerts, and smart lists remain user-keyed.

## API and UI compatibility

Keep existing endpoint URLs and response shapes. The current single home-search configuration per user remains the UI behavior; this change scopes its collected data and job state. Existing run links continue to work for their owner. Requests for another user's run or an unobserved listing return not found, without disclosing whether that ID exists. Shared-catalog mutation routes must no longer let a regular account delete or merge rows that another user's runs reference.

## Failure handling

The migration must be transactional and repeatable through the existing ordered migration runner. A failed migration must leave the prior schema and user data usable. Store methods must apply ownership in SQL predicates, not fetch globally and filter only in application code. Shared-catalog deletion is removed from ordinary user flows. Because the old schema did not record every unchanged sighting, the migration preserves recorded ownership links and assigns fully unlinked legacy listings to the lowest-ID admin as directed; it must not change account credentials.

## Verification

Add store and API coverage with two users who collect the same listing and different listings. Verify result, history, batch, selected-run, deletion, alert, and progress isolation; verify unchanged payloads still associate with both new runs; verify the migration preserves recorded legacy associations, grants unlinked legacy listings only to the lowest-ID admin, and preserves all existing rows and credentials. Run the targeted Python tests and frontend checks as appropriate, then build the Docker image without starting or recreating PostgreSQL.

## Scope limits

This change does not add a multi-search management UI, duplicate the shared property catalog per account, change authentication, or alter the existing PostgreSQL connection. The separate Docker startup issue remains a follow-up from the earlier request.
