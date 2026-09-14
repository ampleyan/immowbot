<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import DetailPanel from '../components/DetailPanel.vue'
import SavePanel from '../components/SavePanel.vue'
import MapView from '../components/MapView.vue'
import ComparisonPanel from '../components/ComparisonPanel.vue'
import FollowUpCalendar from '../components/FollowUpCalendar.vue'
import MapSectionHeader from '../components/MapSectionHeader.vue'
import MultiSelectChips from '../components/MultiSelectChips.vue'
import { getFollowUps, matchesTriage, sortListings } from './listingUtils.js'

const listings = ref([])
const lists = ref([])
const selectedUrl = ref(null)
const savingUrl = ref(null)
const checked = ref(new Set())
const showExcluded = ref(false)
const filterOpen = ref(false)
const sortBy = ref('score')
const comparisonOpen = ref(false)
const mapOpen = ref(false)
const triageFilter = ref('all')
const alerts = ref([])
const listingsLoading = ref(false)
const listingsError = ref('')
const lastLoadedAt = ref(null)
const detailRefs = new Map()

const filters = ref({
  sources: [],
  postcodes: [],
  epc: [],
  minBeds: 0,
  minSqm: 0,
  maxSqm: 0,
  terrace: false,
})

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

function refreshWhenVisible() {
  if (document.visibilityState === 'visible') {
    loadListings()
    loadLists()
    loadAlerts()
  }
}

onMounted(() => {
  loadListings()
  loadLists()
  loadAlerts()
  window.addEventListener('search-config-updated', loadListings)
  window.addEventListener('keydown', handleKeyboard)
  document.addEventListener('visibilitychange', refreshWhenVisible)
})
onUnmounted(() => {
  window.removeEventListener('search-config-updated', loadListings)
  window.removeEventListener('keydown', handleKeyboard)
  document.removeEventListener('visibilitychange', refreshWhenVisible)
})

const passing = computed(() => listings.value.filter(l => l._score !== null))
const excluded = computed(() => listings.value.filter(l => l._score === null))
const followUps = computed(() => getFollowUps(listings.value))
const today = new Date().toISOString().slice(0, 10)
const changedKeys = computed(() => new Set(alerts.value.filter(alert => alert.kind === 'price_reduction' || alert.kind === 'photos_added').map(alert => `${alert.source}:${alert.source_listing_id}`)))
const triageCounts = computed(() => ({
  all: passing.value.length,
  new: passing.value.filter(listing => matchesTriage(listing, 'new', changedKeys.value)).length,
  changed: passing.value.filter(listing => matchesTriage(listing, 'changed', changedKeys.value)).length,
  'follow-up': passing.value.filter(listing => matchesTriage(listing, 'follow-up', changedKeys.value)).length,
}))

const filterableListings = computed(() => showExcluded.value ? listings.value : passing.value)
const availableSources = computed(() => [...new Set(filterableListings.value.map(l => l.source).filter(Boolean))].sort())
const availablePostcodes = computed(() => [...new Set(filterableListings.value.map(l => l.postcode).filter(Boolean))].sort())
const availableEpc = computed(() => ALL_EPC.filter(epc => filterableListings.value.some(listing => listing.epc_score === epc)))

const displayList = computed(() => {
  let list = [...passing.value, ...(showExcluded.value ? excluded.value : [])]
  const f = filters.value
  if (f.sources.length) list = list.filter(l => f.sources.includes(l.source))
  if (f.postcodes.length) list = list.filter(l => f.postcodes.includes(l.postcode))
  if (f.epc.length) list = list.filter(l => f.epc.includes(l.epc_score))
  if (f.minBeds > 0) list = list.filter(l => (l.bedrooms || 0) >= f.minBeds)
  if (f.minSqm > 0) list = list.filter(l => (l.surface_area || 0) >= f.minSqm)
  if (f.maxSqm > 0) list = list.filter(l => (l.surface_area || 0) <= f.maxSqm)
  if (f.terrace) list = list.filter(l => l.outdoor_terrace || l.outdoor_surface)
  list = list.filter(l => matchesTriage(l, triageFilter.value, changedKeys.value))
  const matching = sortListings(list.filter(l => l._score !== null), sortBy.value)
  const excludedResults = sortListings(list.filter(l => l._score === null), sortBy.value)
  return [...matching, ...(showExcluded.value ? excludedResults : [])]
})

const nChecked = computed(() => checked.value.size)
const comparisonListings = computed(() => listings.value.filter(l => checked.value.has(l.url)).slice(0, 5))
const withoutCoordinates = computed(() => displayList.value.filter(l => l.latitude === null || l.latitude === undefined || l.latitude === '' || l.longitude === null || l.longitude === undefined || l.longitude === '' || !Number.isFinite(Number(l.latitude)) || !Number.isFinite(Number(l.longitude))).length)

function toggleCheck(url) {
  const s = new Set(checked.value)
  if (s.has(url)) s.delete(url)
  else s.add(url)
  checked.value = s
}

function selectAll() {
  checked.value = new Set(displayList.value.map(l => l.url))
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
  const rejectionReason = status === 'Rejected' ? window.prompt('Why are you rejecting this property?', listing._workflow?.rejection_reason || '') : ''
  if (status === 'Rejected' && rejectionReason === null) return
  try {
    await api.saveWorkflow(listing.source, String(listing.source_listing_id), { ...(listing._workflow || {}), status, rejection_reason: rejectionReason || '' })
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

const activeFilterCount = computed(() => filters.value.sources.length + filters.value.postcodes.length + filters.value.epc.length + (filters.value.minBeds > 0 ? 1 : 0) + (filters.value.minSqm > 0 ? 1 : 0) + (filters.value.maxSqm > 0 ? 1 : 0) + (filters.value.terrace ? 1 : 0))

function clearFilters() {
  filters.value = { sources: [], postcodes: [], epc: [], minBeds: 0, minSqm: 0, maxSqm: 0, terrace: false }
}

</script>

<template>
  <div>
    <div v-if="listingsLoading" class="data-status">Refreshing listings…</div>
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

    <div v-if="!listings.length" class="empty">No listings yet. Run a collection from the sidebar.</div>

    <template v-else>
      <div class="show-excluded-row">
        <input type="checkbox" id="show-excluded" v-model="showExcluded" />
        <label for="show-excluded">Show excluded ({{ excluded.length }})</label>
      </div>

      <div class="filter-bar">
        <div class="filter-bar-header">
          <button class="filter-bar-toggle" @click="filterOpen = !filterOpen">
            <span class="filter-title">Filters <span v-if="activeFilterCount" class="filter-count">{{ activeFilterCount }}</span></span>
            <span class="filter-chevron" aria-hidden="true">{{ filterOpen ? '⌃' : '⌄' }}</span>
          </button>
          <button v-if="activeFilterCount" class="filter-clear" type="button" @click="clearFilters">Clear all</button>
        </div>
        <div v-if="filterOpen" class="filter-bar-body">
          <div class="filter-group">
            <div class="filter-group-label">Where</div>
            <div class="filter-group-fields">
              <div class="filter-field">
                <label>Portal</label>
                <MultiSelectChips v-model="filters.sources" :options="availableSources" placeholder="All portals" />
              </div>
              <div class="filter-field">
                <label>Postcode</label>
                <MultiSelectChips v-model="filters.postcodes" :options="availablePostcodes" placeholder="All postcodes" />
              </div>
            </div>
          </div>
          <div class="filter-group">
            <div class="filter-group-label">Property</div>
            <div class="filter-group-fields">
              <div class="filter-field">
                <label>EPC</label>
                <MultiSelectChips v-model="filters.epc" :options="availableEpc" placeholder="All EPC grades" />
              </div>
              <div class="filter-field filter-number-fields">
                <label>Bedrooms</label>
                <input type="number" v-model.number="filters.minBeds" min="0" step="1" placeholder="Min" />
                <label>Surface area</label>
                <div class="filter-range"><input type="number" v-model.number="filters.minSqm" min="0" step="5" placeholder="Min m²" /><input type="number" v-model.number="filters.maxSqm" min="0" step="5" placeholder="Max m²" /></div>
              </div>
            </div>
            <label class="filter-check"><input type="checkbox" id="terrace-filter" v-model="filters.terrace" /> Terrace or garden</label>
          </div>
        </div>
      </div>

      <div class="triage-panel">
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
          <MapView :listings="displayList" @select="toggleDetail" />
        </div>
      </div>

      <div class="mobile-review-hint">Mobile review: tap a card to open it, or use Shortlist / Reject.</div>

      <template v-for="listing in displayList" :key="listing.url">
        <PropertyCard
          :listing="listing"
          :isSelected="selectedUrl === listing.url"
          :isSaving="savingUrl === listing.url"
          :isChecked="checked.has(listing.url)"
          @toggle-select="toggleCheck(listing.url)"
          @toggle-detail="toggleDetail(listing.url)"
          @toggle-save="toggleSave(listing.url)"
          @quick-status="quickStatus(listing, $event)"
        />
        <SavePanel
          v-if="savingUrl === listing.url"
          :listing="listing"
          :allLists="lists"
          @updated="onPanelUpdated"
        />
        <DetailPanel
          v-if="selectedUrl === listing.url"
          :ref="element => setDetailRef(listing.url, element)"
          :listing="listing"
          @updated="onPanelUpdated"
        />
      </template>
    </template>
  </div>
</template>
