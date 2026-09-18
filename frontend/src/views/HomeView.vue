<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { getFollowUps, isNewListing, isPendingReview, listingKey } from './listingUtils.js'

type DashboardListing = Parameters<typeof isNewListing>[0] & { _exclusions?: unknown[] }
type DashboardAlert = { kind?: string; source?: string; source_listing_id?: string | number; read_at?: string | null }

const dashboardApi = api as {
  listings: () => Promise<DashboardListing[]>
  getAlerts: () => Promise<DashboardAlert[]>
}

const props = withDefaults(defineProps<{
  collectionState?: { alive?: boolean }
}>(), {
  collectionState: () => ({ alive: false }),
})

const listings = ref<DashboardListing[]>([])
const alerts = ref<DashboardAlert[]>([])
const loading = ref(true)
const error = ref('')

const activeListings = computed(() => listings.value.filter(listing => !listing._exclusions?.length))
const changedKeys = computed(() => new Set(
  alerts.value
    .filter(alert => alert.kind === 'price_reduction' || alert.kind === 'photos_added')
    .map(alert => `${alert.source}:${alert.source_listing_id}`),
))
const reviewCount = computed(() => activeListings.value.filter(isPendingReview).length)
const newCount = computed(() => activeListings.value.filter(listing => isNewListing(listing)).length)
const changedCount = computed(() => activeListings.value.filter(listing => changedKeys.value.has(listingKey(listing))).length)
const followUpCount = computed(() => getFollowUps(activeListings.value).length)
const unreadAlertCount = computed(() => alerts.value.filter(alert => !alert.read_at).length)
const runLabel = computed(() => props.collectionState.alive ? 'Collection is running' : 'Ready for a new search')

const actionCards = computed(() => [
  { key: 'new', label: 'New today', count: newCount.value, href: '/active?triage=new', action: 'Review new' },
  { key: 'changed', label: 'Changed', count: changedCount.value, href: '/active?triage=changed', action: 'Review changes' },
  { key: 'follow-up', label: 'Follow-ups', count: followUpCount.value, href: '/active?triage=follow-up', action: 'Open follow-ups' },
  { key: 'review', label: 'To review', count: reviewCount.value, href: '/active', action: 'Open review queue' },
])

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [loadedListings, loadedAlerts] = await Promise.all([dashboardApi.listings(), dashboardApi.getAlerts()])
    listings.value = loadedListings
    alerts.value = loadedAlerts
  } catch (loadError: unknown) {
    error.value = loadError instanceof Error ? loadError.message : 'Could not load your property brief.'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <main class="home-dashboard">
    <header class="home-hero">
      <div>
        <p class="home-kicker">Property brief</p>
        <h1>Know what deserves your attention.</h1>
        <p class="home-intro">A focused view of the listings that changed, arrived, or need a follow-up.</p>
      </div>
      <div :class="['home-run-status', { running: collectionState.alive }]" role="status">
        <span class="home-status-dot" aria-hidden="true" />
        <span>{{ runLabel }}</span>
      </div>
    </header>

    <div v-if="error" class="home-error" role="alert">{{ error }}</div>

    <section class="home-summary" aria-label="Property summary">
      <div class="home-summary-total">
        <span class="home-summary-value">{{ loading ? '—' : activeListings.length }}</span>
        <span class="home-summary-label">active properties</span>
      </div>
      <RouterLink class="home-summary-link" to="/active">Open all listings</RouterLink>
    </section>

    <section class="home-actions" aria-label="Triage actions">
      <article v-for="card in actionCards" :key="card.key" class="home-action-card" :class="`home-action-${card.key}`">
        <div class="home-action-topline">
          <span class="home-action-label">{{ card.label }}</span>
          <span class="home-action-count">{{ loading ? '—' : card.count }}</span>
        </div>
        <RouterLink class="home-action-link" :to="card.href">{{ card.action }} <span aria-hidden="true">→</span></RouterLink>
      </article>
    </section>

    <section class="home-next-step">
      <div>
        <p class="home-kicker">Next step</p>
        <h2>{{ reviewCount ? `${reviewCount} properties are waiting for your decision` : 'Your review queue is clear' }}</h2>
        <p v-if="reviewCount">Start with the highest-priority listings, then move them into your buying pipeline.</p>
        <p v-else>Run a new collection or check your follow-ups to keep momentum.</p>
      </div>
      <RouterLink class="home-primary-action" to="/active">{{ reviewCount ? 'Start reviewing' : 'View listings' }}</RouterLink>
    </section>

    <section class="home-footer-row">
      <div class="home-footer-note">
        <span class="home-footer-number">{{ unreadAlertCount }}</span>
        <span><strong>{{ unreadAlertCount ? 'unread alerts' : 'No unread alerts' }}</strong><br />Changes worth checking are collected here.</span>
      </div>
      <RouterLink class="home-secondary-action" to="/alerts">Open alerts</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.home-dashboard { max-width: 1120px; margin: 0 auto; padding: 0.5rem 0 2rem; }
.home-hero { display: flex; justify-content: space-between; align-items: flex-start; gap: 2rem; padding: 1.25rem 0 2rem; }
.home-kicker { color: #b02a6f; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.45rem; }
.home-hero h1 { max-width: 620px; color: #101828; font-size: clamp(2rem, 4vw, 3.25rem); line-height: 1.05; letter-spacing: -0.045em; font-weight: 700; }
.home-intro { max-width: 560px; color: #667085; font-size: 1rem; line-height: 1.55; margin-top: 0.9rem; }
.home-run-status { display: inline-flex; align-items: center; gap: 0.5rem; flex-shrink: 0; color: #475467; background: #fff; border: 1px solid #e4e7ec; border-radius: 999px; padding: 0.55rem 0.8rem; font-size: 0.78rem; }
.home-run-status.running { color: #047857; border-color: #a7f3d0; background: #ecfdf3; }
.home-status-dot { width: 0.5rem; height: 0.5rem; background: #98a2b3; border-radius: 50%; }
.running .home-status-dot { background: #10b981; box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.14); }
.home-error { color: #b42318; background: #fef3f2; border: 1px solid #fecdca; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; }
.home-summary { display: flex; align-items: center; justify-content: space-between; gap: 1rem; border-top: 1px solid #e4e7ec; border-bottom: 1px solid #e4e7ec; padding: 1rem 0; }
.home-summary-total { display: flex; align-items: baseline; gap: 0.55rem; }
.home-summary-value { color: #101828; font-size: 1.55rem; font-weight: 700; letter-spacing: -0.03em; }
.home-summary-label { color: #667085; font-size: 0.85rem; }
.home-summary-link, .home-action-link, .home-secondary-action { color: #b02a6f; font-size: 0.8rem; font-weight: 700; text-decoration: none; }
.home-summary-link:hover, .home-action-link:hover, .home-secondary-action:hover { color: #8e2058; text-decoration: underline; }
.home-actions { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin: 1rem 0 2rem; }
.home-action-card { min-height: 132px; display: flex; flex-direction: column; justify-content: space-between; background: #fff; border: 1px solid #e4e7ec; border-top: 3px solid #b02a6f; border-radius: 8px; padding: 1rem; }
.home-action-changed { border-top-color: #d97706; }
.home-action-follow-up { border-top-color: #2563eb; }
.home-action-review { border-top-color: #475467; }
.home-action-topline { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.home-action-label { color: #667085; font-size: 0.78rem; font-weight: 600; }
.home-action-count { color: #101828; font-size: 2rem; font-weight: 700; line-height: 1; }
.home-action-link { align-self: flex-start; }
.home-next-step { display: flex; justify-content: space-between; align-items: center; gap: 2rem; background: #4a102a; color: #fff; border-radius: 10px; padding: 1.5rem 1.75rem; }
.home-next-step .home-kicker { color: #f9a8d4; }
.home-next-step h2 { max-width: 600px; font-size: 1.3rem; line-height: 1.2; letter-spacing: -0.02em; }
.home-next-step p:not(.home-kicker) { color: rgba(255,255,255,0.68); font-size: 0.85rem; line-height: 1.5; margin-top: 0.45rem; }
.home-primary-action { flex-shrink: 0; color: #4a102a; background: #f5c400; border-radius: 6px; padding: 0.7rem 1rem; font-size: 0.8rem; font-weight: 700; text-decoration: none; }
.home-primary-action:hover { background: #ffd733; }
.home-footer-row { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1.25rem 0; }
.home-footer-note { display: flex; align-items: center; gap: 0.75rem; color: #667085; font-size: 0.78rem; line-height: 1.45; }
.home-footer-note strong { color: #344054; }
.home-footer-number { color: #101828; font-size: 1.4rem; font-weight: 700; }
@media (max-width: 760px) {
  .home-hero { flex-direction: column; gap: 1rem; }
  .home-actions { grid-template-columns: repeat(2, 1fr); }
  .home-next-step { align-items: flex-start; flex-direction: column; }
}
@media (max-width: 460px) {
  .home-actions { grid-template-columns: 1fr; }
  .home-summary, .home-footer-row { align-items: flex-start; flex-direction: column; }
}
</style>
