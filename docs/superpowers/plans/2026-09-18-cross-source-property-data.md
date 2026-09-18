# Cross-Source Property Data and Contact Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Immowbot consistently capture the most decision-useful property, agency, timestamp, and contact data from Immoweb, Immoscoop, and Zimmo without losing existing listing history or requiring authentication for public fields.

**Architecture:** Keep source-specific extraction inside each scraper, normalize shared fields through the existing `BasePropertyScraper._normalize_property_data`, and preserve source-specific details in `all_property_details`/category detail objects. Store contact metadata in the existing JSON listing payload; use the existing workflow table only for user-managed contact tracking. The UI will present a compact “Key facts” and “Contact” area in the opened property panel, while cards remain focused on triage.

**Tech Stack:** Python 3.12, Selenium, BeautifulSoup, PostgreSQL JSONB listing payloads, Vue 3, Vitest, unittest.

**Spec:** This plan and the preceding source comparison in the conversation.

## Global Constraints

- Do not add credentials or cookies to the repository, test fixtures, logs, Docker images, or committed configuration.
- Use only user-visible public page data and normal authenticated browser actions; do not bypass CAPTCHA, access controls, or hidden/private APIs.
- Preserve existing `listing_versions` history and avoid creating a new database migration unless the existing JSON payload cannot represent a required field.
- Keep the existing `NEW TO CHECK` semantics: fresh means first seen within 24 hours and unreviewed means no note plus empty/`New` workflow status.
- Do not add inline code comments unless explicitly requested; do not add Python type annotations.
- Each implementation phase touches no more than five files, has its own tests, and ends with a commit.

---

## Completed Baseline

- Fresh/unreviewed tracking is implemented by `isNewToCheck`, the `NEW TO CHECK` card chip, card highlighting, and aligned triage filtering.
- Immoweb contact reveal is implemented in commit `9cdf0b4`; it clicks visible phone/email actions and stores `agent_phone`/`agent_email`.
- Immoscoop already extracts agent name, phone, and email from its structured data.
- Existing listing history, notes, workflow status, and source dates remain the source of truth for review and freshness.

## Target Data Contract

Shared normalized fields to expose whenever a source provides them:

```text
source_created_at
source_updated_at
agent_name
agent_phone
agent_email
agency_name
agency_address
agency_url
bathrooms
floor
epc_value
epc_certificate_number
heating_type
renovation_obligation
renovation_year
monthly_charges
cadastral_income
parking
terrace
garden
solar_panels
investment_property
new_build
p_score
g_score
contact_status
contact_scraped_at
```

Fields that are source-specific or not reliably available remain in `all_property_details` and the existing category detail dictionaries rather than becoming mandatory columns.

### Task 1: Normalize high-value public fields

**Files:**
- Modify: `src/base_scraper.py` in `_normalize_property_data`
- Modify: `src/scrapers/immoweb_scraper.py` in detail extraction
- Modify: `src/scrapers/immoscoop_scraper.py` in structured detail extraction
- Modify: `src/scrapers/zimmo_scraper.py` in `ng-state` and HTML extraction
- Test: `tests/test_source_data_contract.py`

**Interfaces:**
- Each scraper may return source-specific keys.
- `_normalize_property_data(raw_data)` emits the shared contract with empty values when a source does not provide a field.
- Existing `all_property_details`, `property_details`, and category dictionaries remain intact.

- [ ] Write fixture-based tests for one representative listing from each source, asserting the shared fields are present and that missing values stay empty/`None` rather than being guessed.
- [ ] Run `python -m unittest tests.test_source_data_contract -v` and confirm the new tests fail for fields not yet exposed.
- [ ] Add canonical normalized keys for `agency_name`, `agency_address`, `agency_url`, `floor`, `epc_value`, `epc_certificate_number`, `heating_type`, `renovation_obligation`, `monthly_charges`, `cadastral_income`, `p_score`, `g_score`, and boolean feature flags.
- [ ] Map Immoweb’s existing classified data and details table into those keys; preserve the rich description as the source for narrative facts.
- [ ] Map Immoscoop’s existing `propertyDetailGroups` and agent data into the same keys without replacing its category detail dictionaries.
- [ ] Extend Zimmo’s `LISTING_DETAIL_*` state extraction and HTML fallback using the fields visible on the supplied listing; preserve existing image and translation behavior.
- [ ] Rerun the fixture tests, `python -m compileall -q src`, and commit `feat: normalize cross-source property facts`.

### Task 2: Zimmo agency and contact enrichment

**Files:**
- Modify: `src/scrapers/zimmo_scraper.py`
- Modify: `src/scrapers/scraper contact test fixture` or create `tests/test_zimmo_scraper.py`
- Modify: `src/scraper_manager.py` only if the authenticated profile must be configured centrally
- Test: `tests/test_zimmo_scraper.py`

**Interfaces:**
- Add `_reveal_contact_details(driver)` returning `agent_phone`, `agent_email`, `contact_status`, and `contact_scraped_at`.
- Add agency extraction returning `agency_name`, `agency_address`, and `agency_url` from structured data or visible provider markup.
- Return `contact_status` values limited to `available`, `unavailable`, `requires_login`, and `reveal_failed`.

- [ ] Add fake-driver tests proving visible `Bellen`/`Mailen` actions are clicked and revealed contact values are extracted.
- [ ] Add tests for a public page without contact actions and a login-required page; both must return safely without failing the property scrape.
- [ ] Implement public agency extraction first from `ng-state`, JSON-LD, and visible provider markup.
- [ ] Implement normal Selenium clicks only for visible Zimmo contact controls; do not call undocumented endpoints directly and do not bypass authentication barriers.
- [ ] Record `contact_scraped_at` only when contact extraction was attempted and keep the status explicit.
- [ ] Verify an unauthenticated Zimmo scrape still returns the property when contact extraction is unavailable.
- [ ] Run focused Zimmo tests and commit `feat: enrich Zimmo agency and contacts`.

### Task 3: Preserve enriched data across rescans

**Files:**
- Modify: `src/buyer/property_store.py` in `save_listing`
- Modify: `tests/test_property_store.py`
- Modify: `src/buyer/api.py` only if API serialization needs explicit contact/source fields

**Interfaces:**
- A rescan with missing contact data must not erase a previously captured non-empty phone, email, agency, or source timestamp.
- A newly captured non-empty value must replace an empty value but must not create a new listing version when the normalized fingerprint is otherwise unchanged.

- [ ] Add tests that save a listing with contact details, rescan the same listing without them, and assert the latest payload retains the original values.
- [ ] Add tests that save a later non-empty contact value and assert it is updated.
- [ ] Update `save_listing` to merge only enrichment fields that are absent in the incoming payload, leaving ordinary listing changes and version fingerprints unchanged.
- [ ] Confirm description translations are excluded from change detection as already required by the existing behavior.
- [ ] Run the property-store tests and commit `fix: preserve source enrichment during rescans`.

### Task 4: Compact UI for key facts and contacts

**Files:**
- Modify: `frontend/src/components/DetailPanel.vue`
- Modify: `frontend/src/components/PropertyModalPanel.vue` if the right-side panel owns the current detail layout
- Modify: `frontend/src/components/PropertyCard.vue` only for a compact availability chip if needed
- Modify: `frontend/src/style.css`
- Test: corresponding component test files under `frontend/src/components/__tests__/`

**Interfaces:**
- The listing card remains triage-oriented and does not display every field.
- The opened detail panel shows only non-empty facts grouped as `Property`, `Energy`, `Costs & legal`, `Agency`, and `Contact`.
- Contact buttons use existing workflow/contact actions and do not overwrite user-entered workflow data automatically.

- [ ] Add component tests for rendering non-empty key facts, hiding empty facts, showing agency metadata, and showing `Call`, `Email`, or `Copy contact` only when values exist.
- [ ] Add a compact “Contact status” label for unavailable/login-required/reveal-failed states.
- [ ] Add the grouped key-facts layout to the opened property panel and reuse existing formatting helpers for money, dates, units, and links.
- [ ] Keep the list card limited to source, price, main specs, dates, triage chips, and the existing `NEW TO CHECK` marker.
- [ ] Run `npm run type-check`, `npm run test:unit -- --run`, `npm run build-only`, and `git diff --check`; commit `feat: show enriched property facts and contacts`.

### Task 5: End-to-end verification and operational handoff

**Files:**
- Modify: `README.md` or the relevant scraper/Docker documentation
- Test: `tests/test_e2e_smoke.py` only if the existing smoke test can safely run without live credentials

- [ ] Document local authenticated-browser setup without including cookies or tokens.
- [ ] Document which fields are public versus login-dependent and explain `contact_status`.
- [ ] Verify Docker/local scraping still works without an authenticated profile.
- [ ] Run the focused Python suites, frontend checks, and the available full suite in the project environment.
- [ ] Record any environment-only failures separately from regressions and push the final commits.

## Acceptance Criteria

- A listing from any of the three sources preserves all existing fields and gains shared high-value facts where the source provides them.
- Zimmo agency metadata is captured without login; phone/email extraction succeeds only through visible contact actions and reports when unavailable.
- A rescan never deletes previously captured contact or agency data merely because a source temporarily hides it.
- The opened detail panel makes the new information useful without making the main list denser.
- No cookies, JWTs, refresh tokens, or other credentials enter source code, tests, logs, images, commits, or Docker layers.
- All applicable focused tests, type checks, frontend tests, builds, and diff checks pass.

## Stop Conditions

Stop and request direction if implementation requires storing user credentials, bypassing CAPTCHA/access controls, adding a mandatory database migration, changing the definition of a reviewed listing, or expanding into a broad redesign of the list/detail layout.
