# Task 4 Report: Compact UI for key facts and contacts

## Scope

`Listings.vue` opens `PropertyModalPanel.vue`, which renders `DetailPanel.vue` for the property detail content. Task 4 therefore changes `DetailPanel.vue`, its matching component test, and the shared stylesheet. The normalized fields already reach the component on the listing payload, so no API or type file change was needed.

## Implementation

The opened detail panel now renders compact, non-empty fact groups for Property, Energy, Costs & legal, Agency, and Contact. It covers the normalized cross-source fields from Task 1, formats amounts, dates, area, EPC values, links, telephone links, and email links, and preserves the existing contact pipeline data as the source for editable agent details.

The contact status maps only the four supported values:

- `available` → `Contact available`
- `unavailable` → `Contact unavailable`
- `requires_login` → `Requires login`
- `reveal_failed` → `Contact reveal failed`

Call, Email, and Copy contact actions render only when a usable phone or email is available. Listing cards were not changed.

## Tests

Added DetailPanel coverage for populated fact groups, omission of empty facts and actions, agency/link and available-action behavior, and every supported contact status. The focused test was first run red with the new UI absent (7 expected failures), then passed after implementation (13/13).

## Verification

- `npm run type-check` — passed.
- `npm run test:unit -- --run` — passed: 17 files, 64 tests.
- `npm run build-only` — passed.
- `git diff --check` — passed.
- `npx eslint . --quiet` — reports 38 existing repository-wide errors, including conventions already present in unchanged files. No lint fixes were made because they would exceed Task 4 scope.

Vitest emits an existing Vite configuration migration warning about extensionless `vite.config` import; tests still pass.

## Files changed

- `frontend/src/components/DetailPanel.vue`
- `frontend/src/components/__tests__/DetailPanel.spec.ts`
- `frontend/src/style.css`
- `.superpowers/sdd/2026-09-18-cross-source-property-data/task-4-report.md`

No credentials, cookies, inline comments, or Python files were added or changed.
