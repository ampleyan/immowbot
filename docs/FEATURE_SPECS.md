# Immowbot Feature Specifications

## Product goal

Reduce noise between scraping and contacting an agent. Listings remain one canonical record; derived views, scores, smart lists, alerts, and comparisons read from that record.

## Shared invariants

- A listing is uniquely identified by portal and portal listing ID.
- Smart lists are saved rules, never copied listing rows.
- All derived values are recalculated from current listing data and current search/finance settings.
- Historical observations are immutable enough to explain changes.
- Missing data is shown as unknown, never treated as zero or a match.
- User actions (status, notes, reminders, manual overrides) survive scraper updates.
- Postcode and source filters apply before detail fetch and in the UI.

## 1. Smart lists

### Scope

Create rule-based lists that update automatically whenever listings or scoring inputs change.

### Built-in rules

- Contact now: score >= 75 and purchase estimate is affordable.
- Affordable: cash surplus >= 0.
- Cash shortfall: cash surplus < 0.
- New this week: first seen within seven days.
- Terrace or garden: either feature is present.
- Needs review: score below 55 or missing required financial/location data.
- Group by postcode and group by portal.

### Data model

`smart_lists`: id, name, rule JSON, system/user-owned, created/updated timestamps.

Rule fields: score minimum/maximum, affordability state, age window, postcodes, portals, outdoor features, property types, and status values.

### Acceptance criteria

- A rule can be created, edited, disabled, and deleted.
- Results update without duplicating listings.
- A listing can belong to multiple smart lists.
- Built-ins are available after startup and cannot be accidentally deleted.
- Rule evaluation is deterministic and covered by unit tests.

## 2. Property comparison

### Scope

Select two to five listings and compare them side by side.

### Fields

Price, price per m², total score, score components, taxes/VAT, total purchase cost, required cash, estimated loan, cash surplus/shortfall, EPC, surface, bedrooms, postcode, location, construction year, terrace, garden, portal, and first-seen date.

### Acceptance criteria

- Selection is available from cards, map popups, and list views.
- Comparison remains available while switching tabs.
- Missing values render as “Unknown”.
- Rows can be sorted by score, cost, cash requirement, or price per m².
- Removing a property immediately recalculates the comparison layout.

## 3. Change tracking

### Scope

Compare each new observation with the previous observation for the same listing.

### Tracked changes

- Price increased/decreased, with amount and percentage.
- Added/removed photos, with count and thumbnails.
- EPC changes.
- Surface, bedrooms, construction year, terrace/garden, and description changes.
- Listing disappeared from a source and later returned.

### Data model

`listing_changes`: listing ID, observed timestamp, field, old value, new value, change type, acknowledged timestamp.

### Acceptance criteria

- Changes are visible in detail view and history.
- Price reductions are visually prominent.
- A returned listing is distinguished from a genuinely new listing.
- Scraper reruns do not create changes when payload values are unchanged.
- Users can mark changes as read.

## 4. Contact pipeline

### Scope

Track the journey from discovery to decision.

### States

`New → Interested → Contacted → Visit planned → Offer → Rejected`.

States may move backward, except rejected remains explicitly reversible.

### Data model

`listing_workflow`: listing ID, status, contact date, next follow-up date, agent name/phone/email, offer amount, updated timestamp.

Existing notes remain user-owned and are not overwritten by scraper data.

### Acceptance criteria

- Status and follow-up date are editable from detail view.
- Pipeline view groups and counts listings by status.
- Overdue follow-ups are highlighted.
- Agent details are copied from the listing but can be manually corrected.
- Status changes are timestamped.

## 5. Commute and location scoring

### Scope

Score travel distance/time to user-configured destinations.

### Settings

Destination name, address/coordinates, travel mode, desired departure time, and maximum acceptable travel time.

### Behavior

- Geocode destinations once and cache coordinates.
- Calculate walking, cycling, driving, or transit time through a replaceable routing provider.
- Show per-destination distance/time and an aggregate commute score.
- Unknown route data produces an unavailable state, not a zero score.

### Acceptance criteria

- At least one destination can be configured and disabled.
- Results are cached and visibly timestamped.
- Routing failures do not block listing ingestion.
- Commute weight participates in the configurable score total only when enabled.

## 6. Duplicate detection

### Scope

Detect the same property across portals and present one canonical property with source offers.

### Matching signals

Exact normalized address, coordinates within a small radius, normalized surface/bedrooms, price proximity, and image similarity where available.

### Behavior

- Assign match confidence: high, medium, low.
- Never merge automatically below the configured confidence threshold.
- Preserve every source URL and source-specific observation.
- Allow manual merge and unmerge.

### Acceptance criteria

- Duplicate groups show all source offers and latest source status.
- Actions on the canonical property apply consistently to its source offers.
- Unmerge restores independent listings without data loss.
- Matching is explainable through displayed signals.

## 7. Alerts

### Scope

Notify users about meaningful listing events.

### Alert triggers

- New listing matching a smart list.
- Score crossing a configured threshold.
- Price reduction.
- New photos.
- Listing disappears or returns.
- Follow-up becomes due.

### Delivery

Start with an in-app notification center and unread count. Add email/webhook delivery only after event deduplication is stable.

### Acceptance criteria

- Each event is delivered once per listing and rule.
- Alerts link to the affected listing.
- Users can mute a rule or mark alerts read.
- Failed delivery is retried without duplicate visible alerts.

## 8. “Why this property?” explanation

### Scope

Explain the current score in plain language.

### Behavior

- Show the strongest positive contributors and the biggest weaknesses.
- Explain hard-filter exclusions separately from soft-score weaknesses.
- Include finance context: affordable, shortfall, or unavailable.
- Use current configured weights and denominators.

### Example

“Strong match because the property is below budget, has a large surface, and EPC B. Weakness: only one bedroom. Estimated own-cash shortfall: €18,400.”

### Acceptance criteria

- Explanation updates immediately after score or finance settings change.
- It never claims a feature that is unknown.
- Text is deterministic for the same listing/configuration.
- Excluded listings explain the exact exclusion reason.

## Cross-feature UX

- Add a compact toolbar for smart-list, compare, and alert actions.
- Keep detail panel as the shared editing surface for workflow, finance, explanation, and changes.
- Use the same color semantics everywhere: green positive, amber review, red shortfall/problem, gray unknown.
- Keep mobile interactions single-column with sticky comparison/selection actions.

## Delivery sequence

1. Smart-list rule engine and built-in lists.
2. Comparison selection and comparison view.
3. Change snapshots and visual history.
4. Contact pipeline and follow-up dates.
5. “Why this property?” explanation using existing score data.
6. Commute destinations and routing cache.
7. Duplicate groups and manual merge controls.
8. In-app alerts, then external delivery.

## Quality gates

- Unit tests for rule evaluation, finance calculations, change detection, and duplicate confidence.
- API tests for authorization and user-owned mutations.
- Vue component tests for selection, comparison, workflow, and responsive states.
- Type-check, lint, production build, and migration rollback checks before each feature commit.
