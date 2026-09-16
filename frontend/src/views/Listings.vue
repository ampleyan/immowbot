<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import PropertyModalPanel from '../components/PropertyModalPanel.vue'
import SavePanel from '../components/SavePanel.vue'
import MapView from '../components/MapView.vue'
import ComparisonPanel from '../components/ComparisonPanel.vue'
import FollowUpCalendar from '../components/FollowUpCalendar.vue'
import MapSectionHeader from '../components/MapSectionHeader.vue'
import MultiSelectChips from '../components/MultiSelectChips.vue'
import Slider from '@vueform/slider'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import { getFollowUps, hasInsufficientPictures, isPendingReview, matchesTriage, potentialBenefits, sortListings } from './listingUtils.js'

const { collectionState } = defineProps({
  collectionState: { type: Object, required: true },
})

const listings = ref([])
const lists = ref([])
const selectedUrl = ref(null)
const savingUrl = ref(null)
const checked = ref(new Set())
const showExcluded = ref(false)
const filterOpen = ref(false)
const sortBy = ref('score')
const comparisonOpen = ref(false)
const mapOpen = ref(localStorage.getItem('map-open') === 'true')
const mapBoundsFilter = ref(false)
const mapBounds = ref(null)
const reviewedOpen = ref(false)
const triageFilter = ref('all')
const statusFilter = ref('pending')
const mapModalUrl = ref(null)
const mapModalListing = computed(() => mapModalUrl.value ? listings.value.find(l => l.url === mapModalUrl.value) || null : null)

function openMapDetail(url) {
  mapModalUrl.value = url
}
const alerts = ref([])
const listingsLoading = ref(false)
const listingsError = ref('')
const lastLoadedAt = ref(null)
const visibleCount = ref(40)
const lazyLoadTarget = ref(null)
const detailRefs = new Map()
let lazyLoadObserver = null

const searchQuery = ref('')

const FILTER_DEFAULTS = {
  sources: [], postcodes: [], epc: [], benefits: [],
  minBeds: 0, minSqm: 0, maxSqm: 0,
  minPrice: 0, maxPrice: 0, minScore: 0, maxScore: 0,
  minYear: 0, maxYear: 0, maxMonthlyCharges: 0,
  minRating: 0,
  terrace: false, hasParking: false, ownerOccupied: false,
  withoutPicture: false, withDescription: false, dutchOnly: false,
}

function loadSavedFilters() {
  try {
    const saved = localStorage.getItem('listing-filters')
    if (saved) return { ...FILTER_DEFAULTS, ...JSON.parse(saved) }
  } catch {}
  return { ...FILTER_DEFAULTS }
}

const filters = ref(loadSavedFilters())

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

watch(filters, val => localStorage.setItem('listing-filters', JSON.stringify(val)), { deep: true })
watch(mapOpen, val => localStorage.setItem('map-open', String(val)))

onMounted(() => {
  loadListings()
  loadLists()
  loadAlerts()
  window.addEventListener('search-config-updated', loadListings)
  window.addEventListener('keydown', handleKeyboard)
  document.addEventListener('visibilitychange', refreshWhenVisible)
  nextTick(observeLazyLoad)
})
onUnmounted(() => {
  window.removeEventListener('search-config-updated', loadListings)
  window.removeEventListener('keydown', handleKeyboard)
  document.removeEventListener('visibilitychange', refreshWhenVisible)
  lazyLoadObserver?.disconnect()
})

const passing = computed(() => listings.value.filter(l => !l._exclusions?.length))
const excluded = computed(() => listings.value.filter(l => l._exclusions?.length > 0))
const reviewQueue = computed(() => listings.value.filter(isPendingReview))
const reviewedListings = computed(() => sortListings(listings.value.filter(listing => !isPendingReview(listing)), sortBy.value))
const followUps = computed(() => getFollowUps(listings.value))
const today = new Date().toISOString().slice(0, 10)
const changedKeys = computed(() => new Set(alerts.value.filter(alert => alert.kind === 'price_reduction' || alert.kind === 'photos_added').map(alert => `${alert.source}:${alert.source_listing_id}`)))
const triageCounts = computed(() => ({
  all: reviewQueue.value.filter(l => !l._exclusions?.length).length,
  new: reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'new', changedKeys.value)).length,
  changed: reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'changed', changedKeys.value)).length,
  'follow-up': reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'follow-up', changedKeys.value)).length,
}))

const WORKFLOW_STATUSES = ['Interested', 'Contacted', 'Visit planned', 'Offer', 'On hold', 'Rejected']
const statusCounts = computed(() => {
  const counts = { pending: 0, Interested: 0, Contacted: 0, 'Visit planned': 0, Offer: 0, 'On hold': 0, Rejected: 0 }
  for (const l of listings.value) {
    const s = l._workflow?.status
    if (!s || s === 'New') counts.pending++
    else if (s in counts) counts[s]++
  }
  return counts
})

const activeStatusSource = computed(() =>
  statusFilter.value === 'pending'
    ? reviewQueue.value
    : listings.value.filter(l => l._workflow?.status === statusFilter.value)
)

const filterableListings = computed(() => {
  const base = activeStatusSource.value
  return showExcluded.value ? base : base.filter(l => !l._exclusions?.length)
})
const availableSources = computed(() => [...new Set(filterableListings.value.map(l => l.source).filter(Boolean))].sort())
const availablePostcodes = computed(() => [...new Set(filterableListings.value.map(l => l.postcode).filter(Boolean))].sort())
const availableEpc = computed(() => ALL_EPC.filter(epc => filterableListings.value.some(listing => listing.epc_score === epc)))
const availableBenefits = computed(() => [...new Set(filterableListings.value.flatMap(potentialBenefits))].sort())

const displayList = computed(() => {
  const base = activeStatusSource.value
  const basePassing = base.filter(l => !l._exclusions?.length)
  const baseExcluded = base.filter(l => l._exclusions?.length > 0)
  let list = [...basePassing, ...(showExcluded.value ? baseExcluded : [])]
  const f = filters.value
  if (f.sources.length) list = list.filter(l => f.sources.includes(l.source))
  if (f.postcodes.length) list = list.filter(l => f.postcodes.includes(l.postcode))
  if (f.epc.length) list = list.filter(l => f.epc.includes(l.epc_score))
  if (f.minBeds > 0) list = list.filter(l => (l.bedrooms || 0) >= f.minBeds)
  if (f.minSqm > 0) list = list.filter(l => (l.surface_area || 0) >= f.minSqm)
  if (f.maxSqm > 0) list = list.filter(l => (l.surface_area || 0) <= f.maxSqm)
  if (f.minPrice > 0) list = list.filter(l => (l.price || 0) >= f.minPrice)
  if (f.maxPrice > 0) list = list.filter(l => (l.price || 0) <= f.maxPrice)
  if (f.minScore > 0) list = list.filter(l => l._score != null && l._score >= f.minScore)
  if (f.minRating > 0) list = list.filter(l => (l._workflow?.rating || 0) >= f.minRating)
  if (f.maxScore > 0) list = list.filter(l => l._score != null && l._score <= f.maxScore)
  if (f.minYear > 0) list = list.filter(l => l.construction_year && l.construction_year >= f.minYear)
  if (f.maxYear > 0) list = list.filter(l => l.construction_year && l.construction_year <= f.maxYear)
  if (f.terrace) list = list.filter(l => l.outdoor_terrace || l.outdoor_garden || l.outdoor_surface)
  if (f.hasParking) list = list.filter(l => {
    const d = l.all_property_details || {}
    return d['Garage'] || d['Parking indoor'] || d['Parking outdoor'] || d['Parking closed box'] || l.garage || l.parking
  })
  if (f.ownerOccupied) list = list.filter(l => !l.has_tenant)
  if (f.maxMonthlyCharges > 0) list = list.filter(l => !l.monthly_charges || Number(l.monthly_charges) <= f.maxMonthlyCharges)
  if (f.withoutPicture) list = list.filter(hasInsufficientPictures)
  if (f.withDescription) list = list.filter(l => l.description)
  if (f.dutchOnly) list = list.filter(l => l.description && (!l.description_english || l.description_english === l.description))
  if (f.benefits.length) list = list.filter(listing => f.benefits.every(benefit => potentialBenefits(listing).includes(benefit)))
  if (mapBoundsFilter.value && mapBounds.value) {
    const { north, south, east, west } = mapBounds.value
    list = list.filter(l => {
      const lat = Number(l.latitude), lng = Number(l.longitude)
      return Number.isFinite(lat) && Number.isFinite(lng) && lat >= south && lat <= north && lng >= west && lng <= east
    })
  }
  if (statusFilter.value === 'pending') list = list.filter(l => matchesTriage(l, triageFilter.value, changedKeys.value))
  const q = searchQuery.value.trim().toLowerCase()
  if (q) list = list.filter(l => {
    const haystack = [
      l.source_listing_id, l.postcode, l.street, l.city, l.municipality, l.address,
      l.description_english, l.description,
    ].filter(Boolean).join(' ').toLowerCase()
    return haystack.includes(q)
  })
  const matching = sortListings(list.filter(l => !l._exclusions?.length), sortBy.value)
  const excludedResults = sortListings(list.filter(l => l._exclusions?.length > 0), sortBy.value)
  return [...matching, ...(showExcluded.value ? excludedResults : [])]
})
const renderedList = computed(() => displayList.value.slice(0, visibleCount.value))

function loadMore() {
  if (visibleCount.value < displayList.value.length) visibleCount.value += 40
}

function observeLazyLoad() {
  lazyLoadObserver?.disconnect()
  if (!lazyLoadTarget.value || typeof IntersectionObserver === 'undefined') return
  lazyLoadObserver = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) loadMore()
  }, { rootMargin: '500px' })
  lazyLoadObserver.observe(lazyLoadTarget.value)
}

watch(displayList, () => {
  visibleCount.value = 40
  nextTick(observeLazyLoad)
})

const nChecked = computed(() => checked.value.size)
const comparisonListings = computed(() => listings.value.filter(l => !l._is_duplicate && checked.value.has(l.url)).slice(0, 5))
const withoutCoordinates = computed(() => displayList.value.filter(l => l.latitude === null || l.latitude === undefined || l.latitude === '' || l.longitude === null || l.longitude === undefined || l.longitude === '' || !Number.isFinite(Number(l.latitude)) || !Number.isFinite(Number(l.longitude))).length)

function toggleCheck(url) {
  const s = new Set(checked.value)
  if (s.has(url)) s.delete(url)
  else s.add(url)
  checked.value = s
}

function selectAll() {
  checked.value = new Set(displayList.value.filter(l => !l._is_duplicate).map(l => l.url))
}
function deselectAll() {
  checked.value = new Set()
}

function removeComparison(url) {
  const s = new Set(checked.value)
  s.delete(url)
  checked.value = s
}

async function deleteChecked() {
  const toDelete = displayList.value.filter(l => checked.value.has(l.url))
  if (!toDelete.length || !window.confirm(`Delete ${toDelete.length} selected properties?`)) return
  for (const l of toDelete) {
    try { await api.deleteListing(l.source, String(l.source_listing_id)) } catch {}
  }
  checked.value = new Set()
  await loadListings()
}

async function deleteAll() {
  if (!window.confirm(`Delete all ${displayList.value.length} visible properties?`)) return
  for (const l of displayList.value) {
    try { await api.deleteListing(l.source, String(l.source_listing_id)) } catch {}
  }
  checked.value = new Set()
  await loadListings()
}

async function rescrapeChecked() {
  const selected = displayList.value.filter(listing => checked.value.has(listing.url) && !listing._is_duplicate)
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
  const selected = displayList.value.filter(listing => checked.value.has(listing.url))
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
  selectedUrl.value = selectedUrl.value === url ? null : url
  savingUrl.value = null
  if (selectedUrl.value) {
    nextTick(() => detailRefs.get(url)?.$el?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
}

function followUpLabel(date) {
  if (date < today) return 'Overdue'
  if (date === today) return 'Today'
  return 'Due ' + date
}

function setDetailRef(url, element) {
  if (element) detailRefs.set(url, element)
  else detailRefs.delete(url)
}

function toggleSave(url) {
  savingUrl.value = savingUrl.value === url ? null : url
  selectedUrl.value = null
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
  if (mapModalUrl.value) mapModalUrl.value = null
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
  if (event.metaKey || event.ctrlKey || event.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target?.tagName)) return
  if (!displayList.value.length) return
  const currentIndex = displayList.value.findIndex(listing => listing.url === selectedUrl.value)
  if (event.key === 'j' || event.key === 'k') {
    event.preventDefault()
    const nextIndex = currentIndex < 0 ? 0 : Math.max(0, Math.min(displayList.value.length - 1, currentIndex + (event.key === 'j' ? 1 : -1)))
    selectedUrl.value = displayList.value[nextIndex].url
  } else if (event.key === 'Enter') {
    event.preventDefault()
    toggleDetail(selectedUrl.value || displayList.value[0].url)
  } else if (event.key === 's' && currentIndex >= 0) {
    quickStatus(displayList.value[currentIndex], 'Interested')
  } else if (event.key === 'r' && currentIndex >= 0) {
    quickStatus(displayList.value[currentIndex], 'Rejected')
  }
}

const ALL_EPC = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']

const activeFilterCount = computed(() => {
  const f = filters.value
  return f.sources.length + f.postcodes.length + f.epc.length + f.benefits.length +
    (f.minBeds > 0 ? 1 : 0) + (f.minSqm > 0 ? 1 : 0) + (f.maxSqm > 0 ? 1 : 0) +
    (f.minPrice > 0 ? 1 : 0) + (f.maxPrice > 0 ? 1 : 0) +
    (f.minScore > 0 ? 1 : 0) + (f.maxScore > 0 ? 1 : 0) +
    (f.minRating > 0 ? 1 : 0) +
    (f.minYear > 0 ? 1 : 0) + (f.maxYear > 0 ? 1 : 0) +
    (f.terrace ? 1 : 0) + (f.hasParking ? 1 : 0) + (f.ownerOccupied ? 1 : 0) +
    (f.maxMonthlyCharges > 0 ? 1 : 0) +
    (f.withoutPicture ? 1 : 0) + (f.withDescription ? 1 : 0) + (f.dutchOnly ? 1 : 0)
})

function clearFilters() {
  filters.value = { ...FILTER_DEFAULTS }
}

function removeSingleChipFilter(key, value) {
  filters.value[key] = filters.value[key].filter(v => v !== value)
}

const sqmRange = computed({
  get: () => [filters.value.minSqm, filters.value.maxSqm || 500],
  set: ([lo, hi]) => { filters.value.minSqm = lo; filters.value.maxSqm = hi === 500 ? 0 : hi }
})
const priceRange = computed({
  get: () => [filters.value.minPrice, filters.value.maxPrice || 2000000],
  set: ([lo, hi]) => { filters.value.minPrice = lo; filters.value.maxPrice = hi === 2000000 ? 0 : hi }
})
const scoreRange = computed({
  get: () => [filters.value.minScore, filters.value.maxScore || 100],
  set: ([lo, hi]) => { filters.value.minScore = lo; filters.value.maxScore = hi === 100 ? 0 : hi }
})
const yearRange = computed({
  get: () => [filters.value.minYear || 1900, filters.value.maxYear || 2025],
  set: ([lo, hi]) => { filters.value.minYear = lo === 1900 ? 0 : lo; filters.value.maxYear = hi === 2025 ? 0 : hi }
})


</script>

<template>
  <div>
    <div v-if="collectionState.alive" class="scrape-progress-banner" role="status" aria-live="polite">
      <span class="scrape-spinner" aria-hidden="true"></span>
      <span class="scrape-progress-copy"><strong>Scraping listings</strong><span>{{ collectionState.portal || 'All portals' }} · Checked {{ collectionState.checked }} · Saved {{ collectionState.saved }}</span></span>
    </div>
    <div v-if="listingsError" class="data-error" role="alert"><span>{{ listingsError }}</span><button class="btn btn-secondary btn-sm" type="button" @click="loadListings">Retry</button></div>
    <div v-else-if="lastLoadedAt" class="last-updated">Last updated {{ lastLoadedAt.toLocaleTimeString() }}</div>
    <div class="metrics">
      <div class="metric-card">
        <div class="metric-label">In store</div>
        <div class="metric-value">{{ listings.length }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Matching</div>
        <div class="metric-value">{{ passing.length }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Excluded</div>
        <div class="metric-value">{{ excluded.length }}</div>
      </div>
    </div>

    <LoadingSpinner v-if="listingsLoading && !listings.length" label="Loading listings" />
    <div v-if="!listings.length && !listingsLoading" class="empty">No listings yet. Run a collection from the sidebar.</div>
    <div v-else-if="!displayList.length && !listingsLoading" class="empty">No unreviewed listings. Review more properties from Lists or Pipeline.</div>

    <template v-if="listings.length">
      <div class="show-excluded-row">
        <input type="checkbox" id="show-excluded" v-model="showExcluded" />
        <label for="show-excluded">Show excluded ({{ excluded.length }})</label>
      </div>

      <div class="search-bar">
        <input v-model="searchQuery" type="search" class="search-input" placeholder="Search by ID, address, or keyword in description…" />
      </div>

      <div class="filter-bar">
        <div class="filter-bar-header">
          <div v-if="filters.sources.length || filters.postcodes.length || filters.epc.length || filters.benefits.length" class="filter-active-summary">
            <button v-for="s in filters.sources" :key="'src-' + s" class="active-chip" type="button" @click="removeSingleChipFilter('sources', s)">{{ s }} ×</button>
            <button v-for="p in filters.postcodes" :key="'pc-' + p" class="active-chip" type="button" @click="removeSingleChipFilter('postcodes', p)">{{ p }} ×</button>
            <button v-for="e in filters.epc" :key="'epc-' + e" class="active-chip" type="button" @click="removeSingleChipFilter('epc', e)">{{ e }} ×</button>
            <button v-for="b in filters.benefits" :key="'ben-' + b" class="active-chip" type="button" @click="removeSingleChipFilter('benefits', b)">{{ b }} ×</button>
          </div>
          <button class="filter-bar-toggle" @click="filterOpen = !filterOpen">
            <span class="filter-title">{{ filterOpen ? '− Filters' : '+ Filters' }}<span v-if="activeFilterCount" class="filter-count">{{ activeFilterCount }}</span></span>
            <span class="filter-chevron" aria-hidden="true">{{ filterOpen ? '⌃' : '⌄' }}</span>
          </button>
          <button v-if="activeFilterCount" class="filter-clear" type="button" @click="clearFilters">Clear all</button>
        </div>
        <div v-if="filterOpen" class="filter-bar-body">
          <div class="filter-field">
            <label>Portal</label>
            <MultiSelectChips v-model="filters.sources" :options="availableSources" placeholder="All portals" />
          </div>
          <div class="filter-field">
            <label>Postcode</label>
            <MultiSelectChips v-model="filters.postcodes" :options="availablePostcodes" placeholder="All postcodes" />
          </div>
          <div class="filter-field">
            <label>EPC</label>
            <MultiSelectChips v-model="filters.epc" :options="availableEpc" placeholder="All EPC grades" />
          </div>
          <div class="filter-field">
            <label>Potential benefits</label>
            <MultiSelectChips v-model="filters.benefits" :options="availableBenefits" placeholder="Any potential benefit" />
          </div>
          <div class="filter-field filter-sliders-col">
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Bedrooms</span>
                <span class="slider-val">{{ filters.minBeds > 0 ? filters.minBeds + '+' : 'any' }}</span>
              </div>
              <Slider v-model="filters.minBeds" :min="0" :max="10" :step="1" :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Surface (m²)</span>
                <span class="slider-val">{{ sqmRange[0] > 0 || sqmRange[1] < 500 ? sqmRange[0] + ' – ' + sqmRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="sqmRange" :min="0" :max="500" :step="5" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Price</span>
                <span class="slider-val">{{ priceRange[0] > 0 || priceRange[1] < 2000000 ? '€' + Math.round(priceRange[0]/1000) + 'k – €' + Math.round(priceRange[1]/1000) + 'k' : 'any' }}</span>
              </div>
              <Slider v-model="priceRange" :min="0" :max="2000000" :step="5000" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Score</span>
                <span class="slider-val">{{ scoreRange[0] > 0 || scoreRange[1] < 100 ? scoreRange[0] + ' – ' + scoreRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="scoreRange" :min="0" :max="100" :step="5" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Year built</span>
                <span class="slider-val">{{ yearRange[0] > 1900 || yearRange[1] < 2025 ? yearRange[0] + ' – ' + yearRange[1] : 'any' }}</span>
              </div>
              <Slider v-model="yearRange" :min="1900" :max="2025" :step="1" range :show-tooltip="false" class="filter-vslider" />
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Min rating</span>
                <span class="slider-val">{{ filters.minRating > 0 ? filters.minRating + '★+' : 'any' }}</span>
              </div>
              <div class="filter-rating-stars">
                <button v-for="n in 5" :key="n" :class="['filter-star', { filled: n <= filters.minRating }]" @click="filters.minRating = filters.minRating === n ? 0 : n" :title="n + ' star' + (n > 1 ? 's' : '') + '+'">★</button>
              </div>
            </div>
            <div class="filter-slider-field">
              <div class="slider-label-row">
                <span class="filter-slider-label">Monthly charges</span>
                <span class="slider-val">{{ filters.maxMonthlyCharges > 0 ? '≤ €' + filters.maxMonthlyCharges : 'any' }}</span>
              </div>
              <Slider v-model="filters.maxMonthlyCharges" :min="0" :max="5000" :step="50" :show-tooltip="false" class="filter-vslider" />
            </div>
          </div>
          <div class="filter-checks-col">
            <label class="filter-check"><input type="checkbox" id="terrace-filter" v-model="filters.terrace" /> Terrace or garden</label>
            <label class="filter-check"><input type="checkbox" id="parking-filter" v-model="filters.hasParking" /> Has parking / garage</label>
            <label class="filter-check"><input type="checkbox" id="owner-occupied-filter" v-model="filters.ownerOccupied" /> Owner-occupied (no tenant)</label>
            <label class="filter-check"><input type="checkbox" id="without-picture-filter" v-model="filters.withoutPicture" /> Without picture (fewer than 3)</label>
            <label class="filter-check"><input type="checkbox" id="with-description-filter" v-model="filters.withDescription" /> Has description</label>
            <label class="filter-check"><input type="checkbox" id="dutch-only-filter" v-model="filters.dutchOnly" /> Dutch only (not translated)</label>
          </div>
        </div>
      </div>

      <div class="status-panel">
        <button :class="['status-option', { active: statusFilter === 'pending' }]" type="button" @click="statusFilter = 'pending'">
          Pending <span>{{ statusCounts.pending }}</span>
        </button>
        <button v-for="s in WORKFLOW_STATUSES" :key="s" :class="['status-option', { active: statusFilter === s }]" type="button" @click="statusFilter = s">
          {{ s }} <span>{{ statusCounts[s] }}</span>
        </button>
        <a class="status-export-btn" href="/api/export/interested" download title="Export interested properties to Excel">↓ Export</a>
      </div>

      <div v-if="statusFilter === 'pending'" class="triage-panel">
        <strong>Triage</strong>
        <button v-for="option in [{ key: 'all', label: 'All' }, { key: 'new', label: 'New' }, { key: 'changed', label: 'Changed' }, { key: 'follow-up', label: 'Follow-ups' }]" :key="option.key" :class="['triage-option', { active: triageFilter === option.key }]" type="button" @click="triageFilter = option.key">
          {{ option.label }} <span>{{ triageCounts[option.key] }}</span>
        </button>
      </div>

      <div v-if="followUps.length" class="follow-up-panel">
        <div class="follow-up-header"><strong>Follow-ups</strong><span>{{ followUps.length }} open</span></div>
        <div class="follow-up-list">
          <button v-for="item in followUps" :key="item.url" :class="['follow-up-item', { overdue: item._workflow.next_follow_up_date < today }]" type="button" @click="toggleDetail(item.url)">
            <span><strong>{{ item.postcode || item.property_type || 'Property' }}</strong> · {{ item._workflow.status }}</span>
            <span>{{ followUpLabel(item._workflow.next_follow_up_date) }}</span>
          </button>
        </div>
        <FollowUpCalendar :listings="followUps" @select="toggleDetail" />
      </div>

      <div class="toolbar">
        <span :class="['toolbar-count', { 'has-selection': nChecked > 0 }]">
          {{ nChecked > 0 ? `${nChecked} selected` : `${displayList.length} properties` }}
        </span>
        <button class="btn btn-secondary btn-sm" @click="nChecked > 0 ? deselectAll() : selectAll()">
          {{ nChecked > 0 ? 'Deselect all' : 'Select all' }}
        </button>
        <button v-if="nChecked > 0" class="btn btn-danger btn-sm" @click="deleteChecked">
          Delete {{ nChecked }} selected
        </button>
        <button v-if="nChecked > 0" class="btn btn-secondary btn-sm" :disabled="collectionState.alive" @click="rescrapeChecked">
          {{ collectionState.alive ? 'Rescraping…' : 'Rescrape selected' }}
        </button>
        <button v-if="nChecked > 0" class="btn btn-secondary btn-sm" :disabled="translating" @click="translateChecked">
          {{ translating ? 'Translating…' : 'Translate selected' }}
        </button>
        <button v-else-if="displayList.length" class="btn btn-secondary btn-sm" @click="deleteAll">
          Delete all {{ displayList.length }}
        </button>
        <label class="sort-control" for="sort-listings">
          Sort
          <select id="sort-listings" v-model="sortBy">
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

      <button v-if="nChecked >= 2" type="button" class="floating-compare" @click="comparisonOpen = true">
        Compare {{ Math.min(nChecked, 5) }}<span v-if="nChecked > 5"> of {{ nChecked }}</span>
      </button>

      <ComparisonPanel v-if="comparisonOpen && comparisonListings.length >= 2" :listings="comparisonListings" :all-lists="lists" @remove="removeComparison" @updated="onPanelUpdated" @close="comparisonOpen = false" />

      <div class="map-section">
        <MapSectionHeader :open="mapOpen" :mapped="displayList.length - withoutCoordinates" :withoutCoordinates="withoutCoordinates" @toggle="mapOpen = !mapOpen" />
        <div v-if="mapOpen" id="listing-map-panel" class="map-section-body">
          <div class="map-filter-bar">
            <button :class="['map-bounds-toggle', { active: mapBoundsFilter }]" type="button" @click="mapBoundsFilter = !mapBoundsFilter">
              {{ mapBoundsFilter ? '⊠ Filtering by map view' : '⊡ Filter by map view' }}
            </button>
          </div>
          <MapView :listings="displayList" @select="openMapDetail" @bounds-change="mapBounds = $event" />
        </div>
      </div>

      <div class="mobile-review-hint">Mobile review: tap a card to open it, or use + / ♥.</div>

      <div class="cards-grid">
        <template v-for="listing in renderedList" :key="listing.url">
          <PropertyCard
            :listing="listing"
            :isSaving="savingUrl === listing.url"
            :isChecked="checked.has(listing.url)"
            :showSelect="!listing._is_duplicate"
            @toggle-select="toggleCheck(listing.url)"
            @toggle-detail="toggleDetail(listing.url)"
            @toggle-save="toggleSave(listing.url)"
            @quick-status="quickStatus(listing, $event)"
            @reject="handleReject(listing, $event)"
            @updated="onPanelUpdated"
          />
          <SavePanel
            v-if="savingUrl === listing.url"
            :listing="listing"
            :allLists="lists"
            @updated="onPanelUpdated"
          />
          <PropertyModalPanel
            v-if="selectedUrl === listing.url"
            :ref="element => setDetailRef(listing.url, element)"
            :listing="listing"
            :inline="true"
            @updated="onPanelUpdated"
            @close="selectedUrl = null"
          />
        </template>
        <div v-if="renderedList.length < displayList.length" ref="lazyLoadTarget" class="lazy-load-status" role="status">Loading more listings…</div>
      </div>

      <section v-if="statusFilter === 'pending'" class="reviewed-section">
        <button class="reviewed-toggle" type="button" :aria-expanded="reviewedOpen" @click="reviewedOpen = !reviewedOpen">
          <span>Reviewed listings <span class="reviewed-count">{{ reviewedListings.length }}</span></span>
          <span aria-hidden="true">{{ reviewedOpen ? '⌃' : '⌄' }}</span>
        </button>
        <div v-if="reviewedOpen" class="cards-grid reviewed-list">
          <template v-for="listing in reviewedListings" :key="listing.url">
            <PropertyCard
              :listing="listing"
              :isSaving="savingUrl === listing.url"
              :isChecked="checked.has(listing.url)"
              :showSelect="!listing._is_duplicate"
              @toggle-select="toggleCheck(listing.url)"
              @toggle-detail="toggleDetail(listing.url)"
              @toggle-save="toggleSave(listing.url)"
              @quick-status="quickStatus(listing, $event)"
              @reject="handleReject(listing, $event)"
              @updated="onPanelUpdated"
            />
            <SavePanel v-if="savingUrl === listing.url" :listing="listing" :allLists="lists" @updated="onPanelUpdated" />
            <PropertyModalPanel v-if="selectedUrl === listing.url" :ref="element => setDetailRef(listing.url, element)" :listing="listing" :inline="true" @updated="onPanelUpdated" @close="selectedUrl = null" />
          </template>
        </div>
      </section>
    </template>
  </div>

  <Teleport to="body">
    <div v-if="mapModalListing" class="modal-backdrop" @click.self="mapModalUrl = null">
      <PropertyModalPanel :listing="mapModalListing" :showClose="true" @updated="onPanelUpdated" @close="mapModalUrl = null" />
    </div>
  </Teleport>
</template>
