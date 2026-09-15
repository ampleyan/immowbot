<script setup>
const emit = defineEmits(['close'])

defineProps({
  version: { type: String, default: '' },
})
</script>

<template>
  <div class="help-backdrop" @click.self="emit('close')">
    <div class="help-modal">
      <div class="help-header">
        <span class="help-title">Help & What's New</span>
        <span v-if="version" class="help-version">v{{ version }}</span>
        <button class="help-close" @click="emit('close')">×</button>
      </div>

      <div class="help-body">

        <section class="help-section">
          <h3>What's new in v{{ version || '1.1.0' }}</h3>
          <ul>
            <li><strong>Alerts tab</strong> — new matches shown as scored cards with inline detail panel</li>
            <li><strong>Score circle</strong> — score shown as circle overlay on listing photo (green ≥80, yellow 60–79, red &lt;60)</li>
            <li><strong>Translate selected</strong> — select listings and translate descriptions on demand; progress shown in sidebar</li>
            <li><strong>New score bonuses</strong> — parking (+5), price/m² vs postcode avg (+0–10), price reduced (+5), fresh listing (+5), stale listing (−5), tenant (−10), high charges (up to −10)</li>
            <li><strong>New filters</strong> — score range, price range, construction year, max monthly charges, has parking, owner-occupied</li>
            <li><strong>Card badges</strong> — ↓ price reduced, tenant in place, €X/mo charges, 🅿 parking, floor in specs</li>
            <li><strong>JSON backups</strong> — full listing snapshot saved to <code>data/backups/</code> after each run</li>
            <li><strong>Delta scraping</strong> capped at 3 pages to avoid over-fetching</li>
          </ul>
        </section>

        <section class="help-section">
          <h3>Interface guide</h3>

          <h4>Sidebar</h4>
          <ul>
            <li><strong>Search config</strong> — postcodes, price, surface, bedrooms, EPC, portals, scrape mode. Save to apply.</li>
            <li><strong>Purchase feasibility</strong> — income and loan parameters for affordability estimate on each card.</li>
            <li><strong>Commute</strong> — JSON array of destinations; travel times shown per listing.</li>
            <li><strong>Collection</strong> — start/stop scraping. Progress and translation shown live.</li>
          </ul>

          <h4>Active tab</h4>
          <ul>
            <li>Listings that pass your hard filters, sorted by score.</li>
            <li>Triage statuses: <strong>Pending → Interested → Contacted → Visit planned → Offer → Rejected</strong>.</li>
            <li>Use <strong>WHERE</strong> to filter by portal, postcode, EPC, price, score, year, parking, tenant status and more.</li>
            <li>Select listings for bulk delete, rescrape, comparison (up to 5), or translation.</li>
            <li>Click a card to open the detail panel inline — full gallery, description, score breakdown, pipeline, purchase estimate, price history, map.</li>
            <li>Arrow keys navigate between cards when a panel is open.</li>
          </ul>

          <h4>Alerts tab</h4>
          <ul>
            <li>Shows new listing matches since last cleared. Badge count on tab.</li>
            <li>Click a card to open its detail panel.</li>
            <li><strong>Clear all</strong> marks alerts as read — cleared alerts never reappear.</li>
          </ul>

          <h4>Lists tab</h4>
          <ul>
            <li>Save listings to named lists (Shortlist, To visit, etc.). A listing can be in multiple lists.</li>
          </ul>

          <h4>Pipeline tab</h4>
          <ul>
            <li>Overview of listings across all workflow statuses.</li>
          </ul>

          <h4>Dupe tab</h4>
          <ul>
            <li>Same property listed on multiple portals. Merge to keep the richer record.</li>
          </ul>

          <h4>History tab</h4>
          <ul>
            <li>Past collection runs with per-portal breakdown.</li>
          </ul>
        </section>

        <section class="help-section">
          <h3>Scoring</h3>
          <p>Listings first pass hard filters (postcode, type, price, surface, bedrooms, EPC, year). Those that fail show as "excluded".</p>
          <table class="help-table">
            <thead><tr><th>Component</th><th>Points</th><th>Condition</th></tr></thead>
            <tbody>
              <tr><td>Price headroom</td><td>0–30</td><td>How far below your max price</td></tr>
              <tr><td>Surface area</td><td>0–25</td><td>How far above your minimum</td></tr>
              <tr><td>Bedrooms</td><td>0–15</td><td>How far above your minimum</td></tr>
              <tr><td>EPC</td><td>0–20</td><td>A++=100%, G=0%</td></tr>
              <tr><td>Completeness</td><td>0–10</td><td>Key fields present</td></tr>
              <tr><td>Outdoor</td><td>+5</td><td>Has terrace / garden</td></tr>
              <tr><td>Parking</td><td>+5</td><td>Garage or parking confirmed</td></tr>
              <tr><td>Price/m² vs avg</td><td>+0–10</td><td>Below postcode average</td></tr>
              <tr><td>Price reduced</td><td>+5</td><td>Any prior version was higher</td></tr>
              <tr><td>Fresh listing</td><td>+5</td><td>First seen &lt;14 days ago</td></tr>
              <tr><td>Stale listing</td><td>−5</td><td>First seen &gt;90 days ago</td></tr>
              <tr><td>Tenant in place</td><td>−10</td><td>Property has active tenant</td></tr>
              <tr><td>Monthly charges</td><td>0 to −10</td><td>Above €150/month, linear</td></tr>
            </tbody>
          </table>
        </section>

      </div>
    </div>
  </div>
</template>
