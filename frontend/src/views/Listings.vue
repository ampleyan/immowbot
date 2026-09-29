<script setup>
defineOptions({ name: 'PropertyListingsView' })
import { ref, computed, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import PropertyModalPanel from '../components/PropertyModalPanel.vue'
import ScrapeProgress from '../components/ScrapeProgress.vue'
import SavePanel from '../components/SavePanel.vue'
import MapView from '../components/MapView.vue'
import ComparisonPanel from '../components/ComparisonPanel.vue'
import FollowUpCalendar from '../components/FollowUpCalendar.vue'
import MapSectionHeader from '../components/MapSectionHeader.vue'
import MultiSelectChips from '../components/MultiSelectChips.vue'
import Slider from '@vueform/slider'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import { formatListingAddress } from './listingUtils.js'
import { useListingReview } from './useListingReview.js'

const props = defineProps({
  collectionState: { type: Object, required: true },
  triageFilter: { type: String, default: 'all' },
})
const { collectionState } = props

const listings = ref([])
const lists = ref([])
const alerts = ref([])
const review = reactive(useListingReview({ listings, alerts, initialTriageFilter: () => props.triageFilter }))
const isMobile = ref(false)
const drawerElement = ref(null)
const mobileDetailOpen = computed(() => isMobile.value && Boolean(review.selectedListing))
let mobileQuery = null
let returnFocus = null
let returnFocusUrl = null
let previousBodyOverflow = ''
let bodyOverflowLocked = false
const savingUrl = ref(null)
const reviewedOpen = ref(false)
const listingsLoading = ref(false)
const listingsError = ref('')
const lastLoadedAt = ref(null)
const visibleCount = ref(40)
const lazyLoadTarget = ref(null)
let lazyLoadObserver = null

async function syncPostcodesFromSearchConfig() {
  try {
    const config = await api.getConfig()
    review.filters = {
      ...review.filters,
      postcodes: [...new Set((config.postcodes || []).map(postcode => String(postcode).trim()).filter(Boolean))],
    }
  } catch {}
}

async function loadActiveView() {
  listingsLoading.value = true
  await syncPostcodesFromSearchConfig()
  await Promise.all([loadListings(), loadLists(), loadAlerts()])
}

async function refreshAfterSearchConfigUpdate() {
  await syncPostcodesFromSearchConfig()
  await loadListings()
}

async function loadListings() {
  listingsLoading.value = true
  listingsError.value = ''
  try {
    listings.value = await api.listings()
    lastLoadedAt.value = new Date()
  } catch (error) {
    listingsError.value = error.message || 'Could not refresh listings.'
  }
  listingsLoading.value = false
}
async function loadLists() {
  try { lists.value = await api.getLists() } catch {}
}
async function loadAlerts() {
  try { alerts.value = await api.getAlerts() } catch {}
}

let scrapeWasActive = collectionState.alive
watch(() => collectionState.alive, async (alive) => {
  if (alive) {
    scrapeWasActive = true
  } else if (scrapeWasActive) {
    scrapeWasActive = false
    await Promise.all([loadListings(), loadLists(), loadAlerts()])
  }
})

function refreshWhenVisible() {
  if (document.visibilityState === 'visible') {
    loadListings()
    loadLists()
    loadAlerts()
  }
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 720px)')
  isMobile.value = mobileQuery.matches
  if (mobileQuery.addEventListener) mobileQuery.addEventListener('change', handleMobileChange)
  else mobileQuery.addListener(handleMobileChange)
  loadActiveView()
  window.addEventListener('search-config-updated', refreshAfterSearchConfigUpdate)
  window.addEventListener('keydown', handleKeyboard)
  document.addEventListener('visibilitychange', refreshWhenVisible)
  nextTick(observeLazyLoad)
})
onUnmounted(() => {
  if (mobileQuery?.removeEventListener) mobileQuery.removeEventListener('change', handleMobileChange)
  else mobileQuery?.removeListener(handleMobileChange)
  document.getElementById('app')?.removeAttribute('inert')
  if (bodyOverflowLocked) {
    document.body.style.overflow = previousBodyOverflow
    bodyOverflowLocked = false
  }
  window.removeEventListener('search-config-updated', refreshAfterSearchConfigUpdate)
  window.removeEventListener('keydown', handleKeyboard)
  document.removeEventListener('visibilitychange', refreshWhenVisible)
  lazyLoadObserver?.disconnect()
})

function handleMobileChange(event) {
  isMobile.value = event.matches
}

watch(mobileDetailOpen, async open => {
  const appRoot = document.getElementById('app')
  if (open) {
    returnFocus = document.activeElement instanceof HTMLElement && document.activeElement !== document.body
      ? document.activeElement
      : null
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    bodyOverflowLocked = true
    appRoot?.setAttribute('inert', '')
    await nextTick()
    drawerElement.value?.focus()
    return
  }

  appRoot?.removeAttribute('inert')
  if (bodyOverflowLocked) document.body.style.overflow = previousBodyOverflow
  bodyOverflowLocked = false
  await nextTick()
  if (returnFocus?.isConnected) {
    returnFocus.focus()
  } else if (returnFocusUrl || review.selectedUrl) {
    const targetUrl = returnFocusUrl || review.selectedUrl
    const trigger = [...document.querySelectorAll('.card-open-detail')]
      .find(element => element.getAttribute('data-listing-url') === targetUrl)
    trigger?.focus()
  }
  returnFocus = null
  returnFocusUrl = null
})

const today = new Date().toISOString().slice(0, 10)
const renderedList = computed(() => review.displayList.slice(0, visibleCount.value))

function loadMore() {
  if (visibleCount.value < review.displayList.length) visibleCount.value += 40
}

function observeLazyLoad() {
  lazyLoadObserver?.disconnect()
  if (!lazyLoadTarget.value || typeof IntersectionObserver === 'undefined') return
  lazyLoadObserver = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) loadMore()
  }, { rootMargin: '500px' })
  lazyLoadObserver.observe(lazyLoadTarget.value)
}

watch(() => review.displayList, () => {
  visibleCount.value = 40
  nextTick(observeLazyLoad)
})

async function deleteChecked() {
  const toDelete = review.displayList.filter(l => review.checked.has(l.url))
  if (!toDelete.length || !window.confirm(`Delete ${toDelete.length} selected ${toDelete.length === 1 ? 'property' : 'properties'} from Immowbot? This permanently removes their saved listing data and cannot be undone.`)) return
  const failed = []
  for (const l of toDelete) {
    try { await api.deleteListing(l.source, String(l.source_listing_id)) } catch { failed.push(l) }
  }
  review.deselectAll()
  await loadListings()
  if (failed.length) listingsError.value = `${toDelete.length - failed.length} deleted; ${failed.length} could not be deleted. Refresh and try again.`
}

async function deleteAll() {
  const toDelete = [...review.displayList]
  if (!toDelete.length || !window.confirm(`Delete all ${toDelete.length} visible ${toDelete.length === 1 ? 'property' : 'properties'} from Immowbot? This permanently removes their saved listing data and cannot be undone.`)) return
  const failed = []
  for (const l of toDelete) {
    try { await api.deleteListing(l.source, String(l.source_listing_id)) } catch { failed.push(l) }
  }
  review.deselectAll()
  await loadListings()
  if (failed.length) listingsError.value = `${toDelete.length - failed.length} deleted; ${failed.length} could not be deleted. Refresh and try again.`
}

async function rescrapeChecked() {
  const selected = review.displayList.filter(listing => review.checked.has(listing.url) && !listing._is_duplicate)
  if (!selected.length || collectionState.alive) return
  try {
    await api.startSelectedRun(selected.map(listing => ({
      source: listing.source,
      source_listing_id: String(listing.source_listing_id),
      url: listing.url,
    })))
  } catch (error) {
    listingsError.value = error.message || 'Could not start the selected rescrape.'
  }
}

const translating = ref(false)
async function translateChecked() {
  const selected = review.displayList.filter(listing => review.checked.has(listing.url))
  if (!selected.length || translating.value) return
  translating.value = true
  try {
    await api.translateSelected(selected.map(l => ({ source: l.source, source_listing_id: String(l.source_listing_id) })))
  } catch (error) {
    listingsError.value = error.message || 'Could not start translation.'
  } finally {
    translating.value = false
  }
}

function toggleDetail(url) {
  if (review.selectedUrl === url) {
    closeDetail()
  } else {
    if (!review.selectedUrl) returnFocusUrl = url
    review.selectedUrl = url
    review.mapOnlyFocused = false
  }
  savingUrl.value = null
}

function closeDetail() {
  review.selectedUrl = null
  review.mapOnlyFocused = false
}

function handleDrawerKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeDetail()
    return
  }
  if (event.key !== 'Tab' || !mobileDetailOpen.value || !drawerElement.value) return
  const focusable = [...drawerElement.value.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
    .filter(element => element.getClientRects().length)
  if (!focusable.length) {
    event.preventDefault()
    drawerElement.value.focus()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === drawerElement.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function openCardContact(url) {
  if (!review.selectedUrl) returnFocusUrl = url
  review.selectedUrl = url
  review.mapOnlyFocused = false
  savingUrl.value = null
}

function followUpLabel(date) {
  if (date < today) return 'Overdue'
  if (date === today) return 'Today'
  return 'Due ' + date
}

function toggleSave(url) {
  savingUrl.value = savingUrl.value === url ? null : url
  review.selectedUrl = null
}

async function onPanelUpdated() {
  await loadListings()
  await loadLists()
}

async function quickStatus(listing, status) {
  try {
    await api.saveWorkflow(listing.source, String(listing.source_listing_id), { ...(listing._workflow || {}), status, rejection_reason: '' })
    await loadListings()
  } catch {}
  if (review.mapModalUrl) review.mapModalUrl = null
}

async function handleReject(listing, reason) {
  try {
    await Promise.all([
      api.saveWorkflow(listing.source, String(listing.source_listing_id), { ...(listing._workflow || {}), status: 'Rejected', rejection_reason: reason || '' }),
      reason ? api.saveNote(listing.source, listing.source_listing_id, reason) : Promise.resolve(),
    ])
    await loadListings()
  } catch {}
}

function handleKeyboard(event) {
  if (mobileDetailOpen.value) return
  if (event.metaKey || event.ctrlKey || event.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target?.tagName)) return
  if (!review.displayList.length) return
  const currentIndex = review.displayList.findIndex(listing => listing.url === review.selectedUrl)
  if (event.key === 'j' || event.key === 'k') {
    event.preventDefault()
    const nextIndex = currentIndex < 0 ? 0 : Math.max(0, Math.min(review.displayList.length - 1, currentIndex + (event.key === 'j' ? 1 : -1)))
    review.selectedUrl = review.displayList[nextIndex].url
  } else if (event.key === 'Enter') {
    event.preventDefault()
    toggleDetail(review.selectedUrl || review.displayList[0].url)
  } else if (event.key === 's' && currentIndex >= 0) {
    quickStatus(review.displayList[currentIndex], 'Interested')
  } else if (event.key === 'r' && currentIndex >= 0) {
    quickStatus(review.displayList[currentIndex], 'Rejected')
  }
}

</script>

<template>
  <div>
    <ScrapeProgress :state="collectionState" @cancel="api.cancelRun" />
    <div v-if="listingsError" class="data-error" role="alert"><span>{{ listingsError }}</span><button class="btn btn-secondary btn-sm" type="button" @click="loadListings">Retry</button></div>
    <div v-else-if="lastLoadedAt" class="last-updated">Last updated {{ lastLoadedAt.toLocaleTimeString() }}</div>
    <div class="metrics">
      <div class="metric-card">
        <div class="metric-label">In store</div>
        <div class="metric-value">{{ listings.length }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Matching</div>
        <div class="metric-value">{{ review.passing.length }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Excluded</div>
        <div class="metric-value">{{ review.excluded.length }}</div>
      </div>
    </div>

    <LoadingSpinner v-if="listingsLoading && !listings.length" label="Loading listings" />
    <div v-if="!listings.length && !listingsLoading" class="empty">No listings yet. Run a collection from the sidebar.</div>
    <div v-else-if="!review.displayList.length && !listingsLoading" class="empty">No unreviewed listings. Review more properties from Lists or Pipeline.</div>

    <template v-if="listings.length">
      <div class="show-excluded-row">
        <input type="checkbox" id="show-excluded" v-model="review.showExcluded" />
        <label for="show-excluded">Show excluded ({{ review.excluded.length }})</label>
      </div>

      <div class="search-bar">
        <label class="search-label" for="listing-search">Search listings</label>
        <input id="listing-search" v-model="review.searchQuery" type="search" class="search-input" placeholder="Address, listing ID, or description" />
      </div>

      <div class="filter-bar">
        <div class="filter-bar-header">
          <div v-if="review.filters.sources.length || review.filters.postcodes.length || review.filters.epc.length || review.filters.benefits.length" class="filter-active-summary">
            <button v-for="s in review.filters.sources" :key="'src-' + s" class="active-chip" type="button" @click="review.removeSingleChipFilter('sources', s)">{{ s }} ×</button>
            <button v-for="p in review.filters.postcodes" :key="'pc-' + p" class="active-chip" type="button" @click="review.removeSingleChipFilter('postcodes', p)">{{ p }} ×</button>
            <button v-for="e in review.filters.epc" :key="'epc-' + e" class="active-chip" type="button" @click="review.removeSingleChipFilter('epc', e)">{{ e }} ×</button>
            <button v-for="b in review.filters.benefits" :key="'ben-' + b" class="active-chip" type="button" @click="review.removeSingleChipFilter('benefits', b)">{{ b }} ×</button>
          </div>
          <button class="filter-bar-toggle" @click="review.filterOpen = !review.filterOpen">
            <span class="filter-title">{{ review.filterOpen ? '− Filters' : '+ Filters' }}<span v-if="review.activeFilterCount" class="filter-count">{{ review.activeFilterCount }}</span></span>
            <span class="filter-chevron" aria-hidden="true">{{ review.filterOpen ? '⌃' : '⌄' }}</span>
          </button>
          <button v-if="review.activeFilterCount" class="filter-clear" type="button" @click="review.clearFilters">Clear all</button>
        </div>
        <div v-if="review.filterOpen" class="filter-bar-body">
          <div class="filter-field">
            <label>Portal</label>
            <MultiSelectChips v-model="review.filters.sources" :options="review.availableSources" placeholder="All portals" />
          </div>
          <div class="filter-field">
            <label>Postcode</label>
            <MultiSelectChips v-model="review.filters.postcodes" :options="review.availablePostcodes" placeholder="All postcodes" />
          </div>
          <div class="filter-field">
            <label>EPC</label>
            <MultiSelectChips v-model="review.filters.epc" :options="review.availableEpc" placeholder="All EPC grades" />
          </div>
          <div class="filter-field">
            <label>Potential benefits</label>
            <MultiSelectChips v-model="review.filters.benefits" :options="review.availableBenefits" placeholder="Any potential benefit" />
          </div>
          <button class="filter-advanced-toggle" type="button" :aria-expanded="review.advancedFiltersOpen" @click="review.advancedFiltersOpen = !review.advancedFiltersOpen">
            {{ review.advancedFiltersOpen ? 'Hide advanced filters' : 'More filters' }}
            <span class="filter-advanced-hint">Price, size, score, features and more</span>
            <span v-if="review.advancedFilterCount" class="filter-count">{{ review.advancedFilterCount }}</span>
          </button>
          <template v-if="review.advancedFiltersOpen">
          <div class="filter-field filter-sliders-col">
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Bedrooms</span>
                <span class="slider-val">{{ review.filters.minBeds > 0 ? review.filters.minBeds + '+' : 'any' }}</span>
              </div>
              <Slider v-model="review.filters.minBeds" :min="0" :max="10" :step="1" :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Surface (m²)</span>
                <span class="slider-val">{{ review.sqmRange[0] > 0 || review.sqmRange[1] < 500 ? review.sqmRange[0] + ' – ' + review.sqmRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="review.sqmRange" :min="0" :max="500" :step="5" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Price</span>
                <span class="slider-val">{{ review.priceRange[0] > 0 || review.priceRange[1] < 2000000 ? '€' + Math.round(review.priceRange[0]/1000) + 'k – €' + Math.round(review.priceRange[1]/1000) + 'k' : 'any' }}</span>
              </div>
              <Slider v-model="review.priceRange" :min="0" :max="2000000" :step="5000" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Score</span>
                <span class="slider-val">{{ review.scoreRange[0] > 0 || review.scoreRange[1] < 100 ? review.scoreRange[0] + ' – ' + review.scoreRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="review.scoreRange" :min="0" :max="100" :step="5" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Year built</span>
                <span class="slider-val">{{ review.yearRange[0] > 1900 || review.yearRange[1] < 2025 ? review.yearRange[0] + ' – ' + review.yearRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="review.yearRange" :min="1900" :max="2025" :step="1" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Min rating</span>
                <span class="slider-val">{{ review.filters.minRating > 0 ? review.filters.minRating + '★+' : 'any' }}</span>
              </div>
              <div class="filter-rating-stars">
                <button v-for="n in 5" :key="n" :class="['filter-star', { filled: n <= review.filters.minRating }]" type="button" @click="review.filters.minRating = review.filters.minRating === n ? 0 : n" :aria-label="`Filter by ${n} stars or more`" :aria-pressed="review.filters.minRating === n" :title="n + ' star' + (n > 1 ? 's' : '') + '+'">{{ n <= review.filters.minRating ? '★' : '☆' }}</button>
              </div>
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Monthly charges</span>
                <span class="slider-val">{{ review.filters.maxMonthlyCharges > 0 ? '≤ €' + review.filters.maxMonthlyCharges : 'any' }}</span>
              </div>
              <Slider v-model="review.filters.maxMonthlyCharges" :min="0" :max="5000" :step="50" :show-tooltip="false" class="filter-vslider" />
            </div>
          </div>
          <div class="filter-checks-col">
            <label class="filter-check"><input type="checkbox" id="terrace-filter" v-model="review.filters.terrace" /> Terrace or garden</label>
            <label class="filter-check"><input type="checkbox" id="parking-filter" v-model="review.filters.hasParking" /> Has parking / garage</label>
            <label class="filter-check"><input type="checkbox" id="owner-occupied-filter" v-model="review.filters.ownerOccupied" /> Owner-occupied (no tenant)</label>
            <label class="filter-check"><input type="checkbox" id="include-under-option-filter" v-model="review.filters.includeUnderOption" /> Include under option</label>
            <label class="filter-check"><input type="checkbox" id="without-picture-filter" v-model="review.filters.withoutPicture" /> Without picture (fewer than 3)</label>
            <label class="filter-check"><input type="checkbox" id="with-description-filter" v-model="review.filters.withDescription" /> Has description</label>
            <label class="filter-check"><input type="checkbox" id="dutch-only-filter" v-model="review.filters.dutchOnly" /> Dutch only (not translated)</label>
          </div>
          </template>
        </div>
      </div>

      <div class="status-panel">
        <button :class="['status-option', { active: review.statusFilter === 'pending' }]" type="button" @click="review.statusFilter = 'pending'">
          Pending <span>{{ review.statusCounts.pending }}</span>
        </button>
        <button v-for="s in review.WORKFLOW_STATUSES" :key="s" :class="['status-option', { active: review.statusFilter === s }]" type="button" @click="review.statusFilter = s">
          {{ s }} <span>{{ review.statusCounts[s] }}</span>
        </button>
        <a class="status-export-btn" href="/api/export/interested" download title="Export interested properties to Excel">↓ Export</a>
      </div>

      <div v-if="review.statusFilter === 'pending'" class="triage-panel">
        <strong>Triage</strong>
        <button v-for="option in [{ key: 'all', label: 'All' }, { key: 'new', label: 'New' }, { key: 'changed', label: 'Changed' }, { key: 'follow-up', label: 'Follow-ups' }]" :key="option.key" :class="['triage-option', { active: review.triageFilter === option.key }]" type="button" @click="review.triageFilter = option.key">
          {{ option.label }} <span>{{ review.triageCounts[option.key] }}</span>
        </button>
      </div>

      <div v-if="review.followUps.length" class="follow-up-panel">
        <div class="follow-up-header"><strong>Follow-ups</strong><span>{{ review.followUps.length }} open</span></div>
        <div class="follow-up-list">
          <button v-for="item in review.followUps" :key="item.url" :class="['follow-up-item', { overdue: item._workflow.next_follow_up_date < today }]" type="button" @click="toggleDetail(item.url)">
            <span><strong>{{ item.postcode || item.property_type || 'Property' }}</strong> · {{ item._workflow.status }}</span>
            <span>{{ followUpLabel(item._workflow.next_follow_up_date) }}</span>
          </button>
        </div>
        <FollowUpCalendar :listings="review.followUps" @select="toggleDetail" />
      </div>

      <div class="toolbar">
        <span :class="['toolbar-count', { 'has-selection': review.nChecked > 0 }]">
          {{ review.nChecked > 0 ? `${review.nChecked} selected` : `${review.displayList.length} properties` }}
        </span>
        <button class="btn btn-secondary btn-sm" @click="review.nChecked > 0 ? review.deselectAll() : review.selectAll()">
          {{ review.nChecked > 0 ? 'Deselect all' : 'Select all' }}
        </button>
        <button v-if="review.nChecked > 0" class="btn btn-danger btn-sm" @click="deleteChecked">
          Delete {{ review.nChecked }} selected
        </button>
        <button v-if="review.nChecked > 0" class="btn btn-secondary btn-sm" :disabled="collectionState.alive" @click="rescrapeChecked">
          {{ collectionState.alive ? 'Rescraping…' : 'Rescrape selected' }}
        </button>
        <button v-if="review.nChecked > 0" class="btn btn-secondary btn-sm" :disabled="translating" @click="translateChecked">
          {{ translating ? 'Translating…' : 'Translate selected' }}
        </button>
        <button v-else-if="review.displayList.length" class="btn btn-secondary btn-sm" @click="deleteAll">
          Delete all {{ review.displayList.length }}
        </button>
        <label class="sort-control" for="sort-listings">
          Sort
          <select id="sort-listings" v-model="review.sortBy">
            <option value="lastUpdated">Latest updated</option>
            <option value="score">Best match</option>
            <option value="price">Price: low to high</option>
            <option value="priceHigh">Price: high to low</option>
            <option value="surface">Largest surface</option>
            <option value="bedrooms">Most bedrooms</option>
            <option value="dateAdded">Date added: newest first</option>
            <option value="distance">Closest to Grote Markt</option>
          </select>
        </label>
      </div>

      <button v-if="review.nChecked >= 2" type="button" class="floating-compare" @click="review.comparisonOpen = true">
        Compare {{ Math.min(review.nChecked, 5) }}<span v-if="review.nChecked > 5"> of {{ review.nChecked }}</span>
      </button>

      <ComparisonPanel v-if="review.comparisonOpen && review.comparisonListings.length >= 2" :listings="review.comparisonListings" :all-lists="lists" @remove="review.removeComparison" @updated="onPanelUpdated" @close="review.comparisonOpen = false" />

      <div v-if="!review.mapOpen" class="map-section map-section-collapsed">
        <MapSectionHeader :open="review.mapOpen" :mapped="review.displayList.length - review.withoutCoordinates" :without-coordinates="review.withoutCoordinates" @toggle="review.mapOpen = !review.mapOpen" />
      </div>

      <div class="mobile-review-hint">Mobile review: tap a card to open it, or use + / ♥.</div>

      <aside v-if="review.mapOpen && !review.selectedListing" class="review-side-panel">
        <div class="map-section">
          <MapSectionHeader :open="review.mapOpen" :mapped="review.displayList.length - review.withoutCoordinates" :without-coordinates="review.withoutCoordinates" @toggle="review.mapOpen = !review.mapOpen" />
          <div id="listing-map-panel" class="map-section-body">
            <div class="map-filter-bar">
              <button :class="['map-bounds-toggle', { active: review.mapBoundsFilter }]" type="button" @click="review.mapBoundsFilter = !review.mapBoundsFilter">
                {{ review.mapBoundsFilter ? '⊠ Filtering by map view' : '⊡ Filter by map view' }}
              </button>
              <button v-if="review.selectedHasCoordinates" :class="['map-bounds-toggle', { active: review.mapOnlyFocused }]" type="button" @click="review.mapOnlyFocused = !review.mapOnlyFocused">
                {{ review.mapOnlyFocused ? '⊡ Show all properties' : '◉ Only selected property' }}
              </button>
            </div>
            <MapView :listings="review.mapListings" :focus-url="review.selectedUrl" :only-focused="review.mapOnlyFocused" @select="review.openMapDetail" @bounds-change="review.mapBounds = $event" />
          </div>
        </div>
      </aside>

      <aside v-if="review.selectedListing" class="property-detail-host">
        <Teleport to="body" :disabled="!isMobile">
          <aside
            ref="drawerElement"
            class="property-drawer"
            :role="isMobile ? 'dialog' : undefined"
            :aria-modal="isMobile ? 'true' : undefined"
            :aria-label="`Property details: ${formatListingAddress(review.selectedListing)}`"
            tabindex="-1"
            @keydown="handleDrawerKeydown"
            @click.self="isMobile && closeDetail()"
          >
            <PropertyModalPanel
              :listing="review.selectedListing"
              :inline="true"
              :showClose="true"
              @updated="onPanelUpdated"
              @close="closeDetail"
            />
          </aside>
        </Teleport>
      </aside>

      <div :class="['review-layout', { 'selected-property': review.selectedListing }]">
        <div class="review-results">
          <div class="cards-grid">
            <template v-for="listing in renderedList" :key="listing.url">
              <PropertyCard
                :listing="listing"
                :isSaving="savingUrl === listing.url"
                :isChecked="review.checked.has(listing.url)"
                :selected="review.selectedUrl === listing.url"
                :showSelect="!listing._is_duplicate"
                @toggle-select="review.toggleCheck(listing.url)"
                @toggle-detail="toggleDetail(listing.url)"
                @contact="openCardContact(listing.url)"
                @toggle-save="toggleSave(listing.url)"
                @quick-status="quickStatus(listing, $event)"
                @reject="handleReject(listing, $event)"
                @updated="onPanelUpdated"
              >
                <template v-if="review.selectedUrl === listing.url && review.selectedHasCoordinates && !isMobile" #expanded-map>
                  <div class="card-expanded-map">
                    <MapView :listings="review.mapListings" :focus-url="review.selectedUrl" compact @select="review.openMapDetail" @bounds-change="review.mapBounds = $event" />
                  </div>
                </template>
              </PropertyCard>
              <SavePanel
                v-if="savingUrl === listing.url"
                :listing="listing"
                :allLists="lists"
                @updated="onPanelUpdated"
              />
            </template>
            <div v-if="renderedList.length < review.displayList.length" ref="lazyLoadTarget" class="lazy-load-status" role="status">Loading more listings…</div>
          </div>

          <section v-if="review.statusFilter === 'pending'" class="reviewed-section">
            <button class="reviewed-toggle" type="button" :aria-expanded="reviewedOpen" @click="reviewedOpen = !reviewedOpen">
              <span>Reviewed listings <span class="reviewed-count">{{ review.reviewedListings.length }}</span></span>
              <span aria-hidden="true">{{ reviewedOpen ? '⌃' : '⌄' }}</span>
            </button>
            <div v-if="reviewedOpen" class="cards-grid reviewed-list">
              <template v-for="listing in review.reviewedListings" :key="listing.url">
                <PropertyCard
                  :listing="listing"
                  :isSaving="savingUrl === listing.url"
                  :isChecked="review.checked.has(listing.url)"
                  :selected="review.selectedUrl === listing.url"
                  :showSelect="!listing._is_duplicate"
                  @toggle-select="review.toggleCheck(listing.url)"
                  @toggle-detail="toggleDetail(listing.url)"
                  @contact="openCardContact(listing.url)"
                  @toggle-save="toggleSave(listing.url)"
                  @quick-status="quickStatus(listing, $event)"
                  @reject="handleReject(listing, $event)"
                  @updated="onPanelUpdated"
                >
                  <template v-if="review.selectedUrl === listing.url && review.selectedHasCoordinates && !isMobile" #expanded-map>
                    <div class="card-expanded-map">
                      <MapView :listings="review.mapListings" :focus-url="review.selectedUrl" compact @select="review.openMapDetail" @bounds-change="review.mapBounds = $event" />
                    </div>
                  </template>
                </PropertyCard>
                <SavePanel v-if="savingUrl === listing.url" :listing="listing" :allLists="lists" @updated="onPanelUpdated" />
              </template>
            </div>
          </section>
        </div>

      </div>
    </template>
  </div>

  <Teleport to="body">
    <div v-if="review.mapModalListing" class="modal-backdrop" @click.self="review.mapModalUrl = null">
      <PropertyModalPanel :listing="review.mapModalListing" :showClose="true" @updated="onPanelUpdated" @close="review.mapModalUrl = null" />
    </div>
  </Teleport>
</template>
