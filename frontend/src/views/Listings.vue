<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import DetailPanel from '../components/DetailPanel.vue'
import SavePanel from '../components/SavePanel.vue'
import MapView from '../components/MapView.vue'
import { sortListings } from './listingUtils.js'

const listings = ref([])
const lists = ref([])
const selectedUrl = ref(null)
const savingUrl = ref(null)
const checked = ref(new Set())
const showExcluded = ref(false)
const filterOpen = ref(false)
const sortBy = ref('score')

const filters = ref({
  sources: [],
  postcodes: [],
  epc: [],
  minBeds: 0,
  minSqm: 0,
  maxSqm: 0,
  terrace: false,
})

let pollTimer = null

async function loadListings() {
  try { listings.value = await api.listings() } catch {}
}
async function loadLists() {
  try { lists.value = await api.getLists() } catch {}
}

onMounted(() => {
  loadListings()
  loadLists()
  pollTimer = setInterval(() => { loadListings(); loadLists() }, 5000)
})
onUnmounted(() => clearInterval(pollTimer))

const passing = computed(() => listings.value.filter(l => l._score !== null))
const excluded = computed(() => listings.value.filter(l => l._score === null))

const availableSources = computed(() => [...new Set(listings.value.map(l => l.source).filter(Boolean))].sort())
const availablePostcodes = computed(() => [...new Set(listings.value.map(l => l.postcode).filter(Boolean))].sort())

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
  const matching = sortListings(list.filter(l => l._score !== null), sortBy.value)
  const excludedResults = sortListings(list.filter(l => l._score === null), sortBy.value)
  return [...matching, ...(showExcluded.value ? excludedResults : [])]
})

const nChecked = computed(() => checked.value.size)
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
}

function toggleSave(url) {
  savingUrl.value = savingUrl.value === url ? null : url
  selectedUrl.value = null
}

async function onPanelUpdated() {
  await loadListings()
  await loadLists()
}

const ALL_EPC = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
</script>

<template>
  <div>
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
        <button class="filter-bar-toggle" @click="filterOpen = !filterOpen">
          <span>Filters</span>
          <span>{{ filterOpen ? '▲' : '▼' }}</span>
        </button>
        <div v-if="filterOpen" class="filter-bar-body">
          <div class="filter-field">
            <label>Portal</label>
            <select v-model="filters.sources" multiple size="3">
              <option v-for="s in availableSources" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div class="filter-field">
            <label>Postcode</label>
            <select v-model="filters.postcodes" multiple size="3">
              <option v-for="p in availablePostcodes" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="filter-field">
            <label>EPC</label>
            <select v-model="filters.epc" multiple size="3">
              <option v-for="e in ALL_EPC" :key="e" :value="e">{{ e }}</option>
            </select>
          </div>
          <div class="filter-field">
            <label>Min beds</label>
            <input type="number" v-model.number="filters.minBeds" min="0" step="1" />
          </div>
          <div class="filter-field">
            <label>Min m²</label>
            <input type="number" v-model.number="filters.minSqm" min="0" step="5" />
          </div>
          <div class="filter-field">
            <label>Max m²</label>
            <input type="number" v-model.number="filters.maxSqm" min="0" step="5" />
          </div>
          <div class="filter-field" style="align-self:end">
            <div class="filter-toggle-row">
              <input type="checkbox" id="terrace-filter" v-model="filters.terrace" />
              <label for="terrace-filter">Terrace / garden</label>
            </div>
          </div>
        </div>
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

      <div class="map-section">
        <div class="map-section-header">
          <span>Map view</span>
          <span class="map-section-meta">{{ displayList.length - withoutCoordinates }} mapped · {{ withoutCoordinates }} without coordinates</span>
        </div>
        <MapView :listings="displayList" @select="toggleDetail" />
      </div>

      <template v-for="listing in displayList" :key="listing.url">
        <PropertyCard
          :listing="listing"
          :isSelected="selectedUrl === listing.url"
          :isSaving="savingUrl === listing.url"
          :isChecked="checked.has(listing.url)"
          @toggle-select="toggleCheck(listing.url)"
          @toggle-detail="toggleDetail(listing.url)"
          @toggle-save="toggleSave(listing.url)"
        />
        <SavePanel
          v-if="savingUrl === listing.url"
          :listing="listing"
          :allLists="lists"
          @updated="onPanelUpdated"
        />
        <DetailPanel
          v-if="selectedUrl === listing.url"
          :listing="listing"
        />
      </template>
    </template>
  </div>
</template>
