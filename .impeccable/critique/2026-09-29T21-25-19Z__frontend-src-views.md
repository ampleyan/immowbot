---
target: frontend/src/views
total_score: 23
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/home/ampleyan/projects/immowbot/frontend/src/views"
timestamp: 2026-09-29T21-25-19Z
slug: frontend-src-views
closed: true
---
## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 2 | Loading and errors appear in some views, while silent catches elsewhere resemble empty data. |
| 2 | Match System / Real World | 3 | Belgian property details, sources, and buyer stages map well to the task. |
| 3 | User Control and Freedom | 2 | Destructive bulk actions have confirmation but little visible recovery. |
| 4 | Consistency and Standards | 2 | Brand and control patterns drift between views. |
| 5 | Error Prevention | 2 | High-impact bulk operations need stronger impact cues. |
| 6 | Recognition Rather Than Recall | 3 | Counts, statuses, active filters, and property facts aid scanning. |
| 7 | Flexibility and Efficiency | 3 | Sorting, filtering, selection, and bulk actions support efficient review. |
| 8 | Aesthetic and Minimalist Design | 2 | Listings stacks filters, status controls, triage, calendar, bulk actions, and map. |
| 9 | Error Recovery | 2 | Load failures and retries are handled unevenly. |
| 10 | Help and Documentation | 2 | A shell help affordance exists, but contextual workflow guidance is limited. |
| **Total** | | **23/40** | **Acceptable — significant improvements needed.** |

## Design Specificity Verdict

Immowbot’s information architecture is grounded in a Belgian buyer’s workflow: criteria, listings, saved lists, pipeline, and follow-up. The views do not yet feel like one authored workspace. The documented “Buyer’s Command Desk” has a compact burgundy rail and neutral work area, while Home introduces oversized marketing-style copy and local color choices; the shell is branded “MAKELAARTJE” even though the product is Immowbot.

The deterministic detector found **1 warning**: `HomeView.vue:133`, where `.home-action-card` combines a 3px colored top border with rounded corners. The detector flags a possible clash where that top accent meets the rounded edge. No false positive was confirmed. Browser visualization was unavailable, so there are no live overlays or screenshot findings.

## Overall Impression

The product has the right buyer-specific information and useful review queues. The main opportunity is to make the Listings work surface easier to operate at a glance, then carry one consistent identity and clear feedback through the other views.

## What’s Working

- Home turns new, changed, follow-up, and review counts into direct queues and gives a clear next step (`HomeView.vue:30–35, 81–99`).
- Listings keeps useful decision context—source, EPC, dimensions, score, updated age, and active filter chips—close to each property (`Listings.vue:577–589`; `PropertyCard.vue:222–240`).
- Pipeline makes follow-up tangible by keeping notes, contact, and status in the workflow (`Pipeline.vue:157–185`).

## Priority Issues

1. **[P1] Listings puts too many controls in the same review surface.** Expanded filters, status and triage selectors, follow-up/calendar options, bulk actions, and map compete for attention (`Listings.vue:577–733`). This increases rescanning and makes it hard to know which controls define the current queue. Keep the essential filters visible, place advanced criteria behind disclosure, and make status and triage composition explicit. **Suggested command:** `$impeccable distill` or `$impeccable layout`.
2. **[P1] High-impact bulk actions have a weak recovery path.** “Delete selected” and “Delete all” sit alongside routine controls, and duplicate cleanup can affect every group (`Listings.vue:705–719`; `Duplicates.vue:87–123`). Show scope and affected counts before action, give destructive controls distinct treatment, and provide undo/restore where possible. **Suggested command:** `$impeccable harden`.
3. **[P1] Brand and visual patterns drift across views.** Home uses a local hero, colors, and type scale (`HomeView.vue:54–64, 111–146`), while the shell says “MAKELAARTJE” (`Sidebar.vue:193–194`). Align the app name and reuse the documented title, accent, spacing, and surface vocabulary. **Suggested command:** `$impeccable polish`.
4. **[P2] Settings autosave does not make committed state easy to trust.** Changes save after a delay, with separate queued service saves (`Settings.vue:105–168`); the view says changes update immediately (`Settings.vue:266–269`). Add stable per-section saving/saved/error feedback and make the applied state visible. **Suggested command:** `$impeccable clarify`.
5. **[P2] Empty and failed-load states can look alike.** Alerts can show only “No new alerts” (`Alerts.vue:48–53`), while History and Lists suppress load errors into empty-like states (`History.vue:11–14`; `Lists.vue:25–29`). Separate “nothing here” from “couldn’t load,” and offer a retry or next step. **Suggested command:** `$impeccable harden`.

## Cognitive Load

Listings is the densest decision surface. Its expanded controls contain four multiselects, seven numeric/range controls, and seven checkboxes, followed by up to eight workflow status choices, triage choices, bulk actions, and eight sort choices (`Listings.vue:591–731`). Multiple clusters exceed four visible choices at once. Group controls by task, disclose advanced criteria, and explain how status and triage combine. Settings repeats search criteria alongside service and database settings (`Settings.vue:231–299`), so separating buyer setup from infrastructure controls would also reduce context switching.

## Emotional Journey

Home’s “Know what deserves your attention” framing and its next-step CTA reduce uncertainty (`HomeView.vue:54–64, 91–99`). Property photos, scores, and compact facts support quick evaluation. Confidence drops around bulk deletion and duplicate cleanup, where confirmation is the visible safety net but undo is not obvious. A score near the property itself would be easier to trust if its meaning were available in context (`PropertyCard.vue:218, 236–240`).

## Persona Red Flags

- **Alex, power user:** Filtering, sorting, and bulk actions help, but the Listings toolbar and filters require repeated scanning; no obvious keyboard workflow appears in the view markup.
- **Sam, accessibility-dependent:** Compact controls need careful focus and target sizing. Clickable run headers built as `div`s (`History.vue:56–63`) and visual status dots may not communicate interaction/state to assistive technology.
- **Riley, stress tester:** History and Lists load failures can resemble empty data, with no visible retry. Users may conclude there are no properties when the request failed.
- **Casey, mobile user:** The Home summary adapts, but Listings’ filters and toolbar require substantial scrolling on narrow screens.

## Minor Observations

- Home’s active-property total can render `undefined` after loading if the summary is unavailable (`HomeView.vue:73–78`).
- Alerts shows “Clear all” even when there are no unread alerts (`Alerts.vue:48–53`).
- Pipeline’s “No properties here” empty columns do not suggest a next step (`Pipeline.vue:143`).
- Visual and responsive findings are source/CSS based; no live browser was available.

## Questions to Consider

- Is Home meant to be an operational command desk or a more welcoming landing surface?
- Which Listings choices belong in the first-pass review, and which can wait behind advanced filters?
- What recovery promise would make buyers comfortable using delete-all and cross-group duplicate cleanup?
