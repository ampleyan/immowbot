# Task 3 Report: Preserve enriched data across rescans

## Summary

Updated `PropertyStore.save_listing` to retain previously captured non-empty source enrichment when a later rescan supplies a missing or empty value. The merge is restricted to the ten requested source/contact enrichment fields.

## Behavior

- A rescan without contact or agency enrichment retains the last non-empty values.
- A later non-empty enrichment value replaces an earlier empty value.
- The merged payload is fingerprinted, so a contact-less rescan of an otherwise unchanged listing does not create a listing version.
- Existing image-history merging and translated-description fingerprint behavior remain unchanged.
- No database migration was added.

## Tests added

- Saves a fully enriched listing, rescans it without enrichment, verifies all enrichment is retained, and verifies the version count stays at one.
- Saves an empty agent email, then a later non-empty agent email, and verifies the value updates with a new listing version.

## API decision

No API change was needed: listing reads already return the stored payload without field filtering, so enrichment fields pass through to API consumers.

## Verification

- `.venv\\Scripts\\python.exe -m unittest tests.test_property_store -v` — 28 tests passed.
- `.venv\\Scripts\\python.exe -m compileall -q src` — passed.
- `git diff --check` — passed.

## Scope and concerns

Only `src/buyer/property_store.py`, `tests/test_property_store.py`, and this required report were changed. No concerns identified.

## Round 1 Fix Report

The enrichment merge now treats whitespace-only strings as missing values. A rescan with `agent_email="   "` retains the previous non-empty email and does not create a listing version when the remaining listing data is unchanged. The merge remains restricted to `SOURCE_ENRICHMENT_FIELDS`.

Added `test_rescan_treats_whitespace_source_enrichment_as_missing` to cover retention and version-count behavior.

Verification after the fix:

- `.venv\\Scripts\\python.exe -m unittest tests.test_property_store -v` — 29 tests passed.
- `.venv\\Scripts\\python.exe -m compileall -q src` — passed.
- `git diff --check` — passed.

No concerns identified.
