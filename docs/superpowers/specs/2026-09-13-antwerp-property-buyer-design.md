# Antwerp Property Buyer Design

## Goal

Create a local buyer-assistant for properties in Antwerp 2000 and 2018. It automatically collects matching sale listings from Immoweb, Immoscoop, and Zimmo, makes the results available in a local dashboard and Excel, and ranks each listing for two purposes: a home purchase and a rental investment.

The system is a research and comparison tool. It must not contact agents, place offers, calculate binding financing advice, or present listing data as legal verification.

## Fixed first-release criteria

The automated sale search includes houses and apartments that meet all of these conditions:

- Postcode 2000 or 2018
- Asking price at most EUR385,000
- At least two bedrooms
- At least 80 square metres of living area
- EPC label A, B, or C

The system refreshes once daily and also exposes a dashboard action to refresh immediately.

## Acquisition and persistence

Each portal collector owns its own search URL construction, result discovery, detail extraction, and failure handling. It must collect only publicly delivered listing content, use conservative request pacing, and report access failures. CAPTCHA bypasses, stealth automation, and undocumented private API calls are out of scope.

The current portal-specific structured-data extractors are reused where they still match the pages. The browser setup is simplified to standard browser automation; selectors and structured payload readers remain confined to their portal collector.

SQLite becomes the source of truth. A refresh run records its start and completion time, source-specific status, and errors. Listings are stored with their source ID and URL; every materially changed capture becomes a version with its observed time and raw extracted fields. This preserves asking-price changes and makes parser changes auditable.

The system creates duplicate candidates across portals from normalized address or coordinates plus type, area, bedroom count, and price. It groups only high-confidence matches, retains all original source records, and leaves uncertain matches ungrouped.

## Scores

Every qualifying sale listing receives both transparent scores from 0 to 100. A failed hard criterion excludes a listing rather than reducing its score.

The home score uses price headroom, living area, bedroom count, EPC grade, and field completeness. The dashboard shows the individual component values and weights.

The investment score uses expected gross rental yield, EPC grade, price, and field completeness. Expected gross yield is explicitly labelled as an estimate:

`annual median asking rent for comparable rentals / asking price`

The rental collector automatically searches the same portals for rental listings in the target postcodes. Comparables must share property type and have reasonably similar area and bedroom count. The dashboard displays the comparable count, median asking rent, and the source observations. It does not claim net yield or account for taxes, vacancy, repair costs, financing, or purchase costs in the first release.

## Dashboard and export

The dashboard is a local Streamlit application with three views:

- A refresh/status view showing the most recent source status and a Refresh now action.
- A sale-listing table and cards, filterable by profile, source, score, EPC, price, area, bedrooms, and duplicate group.
- A detail view showing source links, observed facts, score explanation, price per square metre, rental-yield estimate, change history, and outstanding due-diligence prompts.

Excel export creates a timestamped comparison workbook for the active dashboard filters. It contains the selected listings, their score breakdowns, source URLs, duplicate grouping, rental-yield assumptions, and refresh metadata. SQLite remains authoritative; an export is a snapshot.

## Reliability rules

- One failed portal must not prevent a successful refresh from another portal.
- A portal response lacking a stable identity, asking price, or location is retained only as a failed capture diagnostic, not surfaced as a candidate.
- Missing data is displayed as missing and lowers completeness; it is never inferred from a similarly named field.
- Listings are never silently deleted because a later refresh cannot access a source.
- All scores and estimates display their inputs so the user can judge their reliability.

## Verification

Tests cover source-to-canonical mapping, hard-filter application, score calculations, comparable-rental selection, duplicate candidate matching, persistence of changed versions, source failure isolation, and Excel output. A small fixture per portal keeps scraper contract tests independent of live sites. The dashboard is smoke-tested against a seeded SQLite database.

## Delivery phases

1. Introduce the canonical SQLite store, scoring engine, and fixture-based tests without changing portal behaviour.
2. Adapt the three portal collectors to persist sale and rental records through the store, with source failure isolation.
3. Add the local Streamlit dashboard, refresh command, and Excel snapshot export.
4. Add the daily local scheduler and complete end-to-end verification with representative fixtures.

Each phase is independently usable and verified before the next begins.
