# Task 4: Compact UI for key facts and contacts

Implement the UI slice that makes the new normalized data useful in the opened property panel without making the main listing cards denser. Inspect the current right-side detail component and use the existing owner of that layout; do not duplicate state between panels.

Files:
- Modify the existing opened-detail component, normally `frontend/src/components/PropertyModalPanel.vue` or `frontend/src/components/DetailPanel.vue`; choose the one actually used by `frontend/src/views/Listings.vue`.
- Modify `frontend/src/style.css`.
- Add/modify the matching component test under `frontend/src/components/__tests__/`.
- Modify one additional API/type file only if the normalized fields are demonstrably filtered before reaching the component.

Requirements:
- Show only non-empty facts grouped as Property, Energy, Costs & legal, Agency, and Contact.
- Render shared fields from Task 1: bathrooms, floor, EPC value/certificate, heating, renovation obligation/year, monthly charges, cadastral income, parking, terrace, garden, solar panels, investment/new-build flags, P-score/G-score, agency name/address/website, phone/email, contact status, and source dates when available.
- Reuse existing formatting helpers for dates, money, units, links, telephone, and email.
- Show Call, Email, and Copy contact actions only when the corresponding value exists.
- Show `Contact available`, `Contact unavailable`, `Requires login`, or `Contact reveal failed` for the four contact statuses; do not invent a fifth state.
- Keep the card limited to existing triage content and `NEW TO CHECK`; do not add a large facts grid to every card.
- Add component tests for populated facts, hidden empty facts, agency/contact actions, and contact status.
- Do not add credentials/cookies, inline comments, or Python changes.
- Run `npm run type-check`, `npm run test:unit -- --run`, `npm run build-only`, and `git diff --check`.
- Commit with `feat: show enriched property facts and contacts`.

Write the full report to `.superpowers/sdd/2026-09-18-cross-source-property-data/task-4-report.md`. Return only status, commit, one-line tests, and concerns. Do not push.
