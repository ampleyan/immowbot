<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api.js'
import DuplicateGroup from '../components/DuplicateGroup.vue'
import PropertyCard from '../components/PropertyCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const props = defineProps({ collectionState: { type: Object, default: () => ({}) } })

// ── history ───────────────────────────────────────────────────────────────────
const runs = ref([])
const histLoading = ref(false)
const histLoaded = ref(false)
const expanded = ref(new Set())
const runListings = ref({})

async function loadHistory() {
  histLoading.value = true
  try {
    runs.value = await api.getRuns()
    histLoaded.value = true
  } catch {}
  histLoading.value = false
}

async function toggleRun(runId) {
  const s = new Set(expanded.value)
  if (s.has(runId)) {
    s.delete(runId)
  } else {
    s.add(runId)
    if (!runListings.value[runId]) {
      try { runListings.value[runId] = await api.getRunListings(runId) } catch { runListings.value[runId] = [] }
    }
  }
  expanded.value = s
}

function fmtTime(iso) { return iso ? iso.slice(0, 19).replace('T', ' ') : '?' }
function fmtPrice(p) { return p ? '€' + Math.round(p).toLocaleString('nl-BE') : '—' }

const STATUS = {
  ok: { color: '#039855', dot: '#039855', label: 'OK' },
  partial: { color: '#D97706', dot: '#D97706', label: 'Partial' },
  cancelled: { color: '#667085', dot: '#667085', label: 'Cancelled' },
  running: { color: '#2563EB', dot: '#2563EB', label: 'Running' },
}
function statusInfo(s) { return STATUS[s] || { color: '#344054', dot: '#98A2B3', label: s || '?' } }

// ── duplicates ────────────────────────────────────────────────────────────────
const duplicates = ref([])
const dupLoading = ref(false)
const dupError = ref('')
const dupLoaded = ref(false)

async function loadDuplicates() {
  dupLoading.value = true
  dupError.value = ''
  try {
    duplicates.value = await api.getDuplicates()
    dupLoaded.value = true
  } catch (cause) {
    dupError.value = cause.message || 'Could not load duplicates.'
  }
  dupLoading.value = false
}

// ── stale translations ────────────────────────────────────────────────────────
const staleListings = ref([])
const staleLoading = ref(false)
const staleError = ref('')
const staleLoaded = ref(false)
const retranslating = ref(false)
const staleSelected = ref(new Set())

function staleKey(l) { return `${l.source}::${l.source_listing_id}` }

const allSelected = computed(() =>
  staleListings.value.length > 0 && staleListings.value.every(l => staleSelected.value.has(staleKey(l)))
)

function toggleSelectAll() {
  if (allSelected.value) {
    staleSelected.value = new Set()
  } else {
    staleSelected.value = new Set(staleListings.value.map(staleKey))
  }
}

function toggleOne(l) {
  const s = new Set(staleSelected.value)
  const k = staleKey(l)
  if (s.has(k)) s.delete(k)
  else s.add(k)
  staleSelected.value = s
}

async function loadStale() {
  staleLoading.value = true
  staleError.value = ''
  staleSelected.value = new Set()
  try {
    const r = await api.listStale()
    const ids = r.listings.map(l => ({ source: l.source, source_listing_id: l.source_listing_id }))
    staleListings.value = ids.length ? await api.getListingsBatch(ids) : []
    staleLoaded.value = true
  } catch (cause) {
    staleError.value = cause.message || 'Could not load stale listings.'
  }
  staleLoading.value = false
}

async function retranslateAll() {
  retranslating.value = true
  try { await api.translateStale() } catch {}
  retranslating.value = false
}

async function retranslateSelected() {
  const selected = staleListings.value.filter(l => staleSelected.value.has(staleKey(l)))
  if (!selected.length) return
  retranslating.value = true
  try {
    await api.translateSelected(selected.map(l => ({ source: l.source, source_listing_id: l.source_listing_id })))
  } catch {}
  retranslating.value = false
}

const translatingId = ref(null)

async function refreshStaleCard(source_listing_id) {
  if (!staleLoaded.value) return
  const existing = staleListings.value.find(l => String(l.source_listing_id) === String(source_listing_id))
  if (!existing) return
  try {
    const fresh = await api.getListingsBatch([{ source: existing.source, source_listing_id: existing.source_listing_id }])
    if (fresh && fresh.length) {
      const idx = staleListings.value.findIndex(l => String(l.source_listing_id) === String(source_listing_id))
      if (idx !== -1) staleListings.value[idx] = fresh[0]
    }
  } catch {}
}

// When translation_current changes, the previous listing just finished — refresh it in place
watch(() => props.collectionState?.translation_current, async (cur, prev) => {
  translatingId.value = cur || null
  if (prev) await refreshStaleCard(prev)
})

// When translation fully finishes, refresh the last card and clear spinner
watch(() => props.collectionState?.translating, async (active, wasActive) => {
  if (!wasActive || active) return
  const last = translatingId.value
  translatingId.value = null
  if (last) await refreshStaleCard(last)
})

function onUpdated() {}

const staleOpen = ref(true)
const dupOpen = ref(true)
const histOpen = ref(true)
</script>

<template>
  <section class="tools-view">
    <h1 class="tools-title">Tools</h1>

    <!-- Stale translations -->
    <div class="tools-section">
      <div class="tools-section-header tools-section-toggle" @click="staleOpen = !staleOpen">
        <div>
          <h2>Stale translations <span class="section-count" v-if="staleLoaded">({{ staleListings.length }})</span></h2>
          <p>Listings where the English description is missing, identical to Dutch, or still contains Dutch text.</p>
        </div>
        <div class="tools-actions" @click.stop>
          <button class="btn btn-secondary" :disabled="staleLoading" @click="loadStale">
            {{ staleLoading ? 'Checking…' : staleLoaded ? 'Refresh' : 'Show stale' }}
          </button>
          <template v-if="staleLoaded && staleListings.length">
            <button v-if="staleSelected.size > 0" class="btn btn-primary" :disabled="retranslating" @click="retranslateSelected">
              {{ retranslating ? 'Queued…' : `Translate selected (${staleSelected.size})` }}
            </button>
            <button v-else class="btn btn-secondary" :disabled="retranslating" @click="retranslateAll">
              {{ retranslating ? 'Queued…' : `Re-translate all (${staleListings.length})` }}
            </button>
          </template>
          <span :class="['section-chevron', { open: staleOpen }]">▼</span>
        </div>
      </div>
      <template v-if="staleOpen">
      <LoadingSpinner v-if="staleLoading" label="Checking stale translations" />
      <div v-else-if="staleError" class="data-error">{{ staleError }}</div>
      <div v-else-if="staleLoaded && !staleListings.length" class="empty">All translations look good.</div>
      <template v-else-if="staleLoaded">
        <div class="stale-select-bar">
          <label class="stale-select-all">
            <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
            {{ allSelected ? 'Deselect all' : 'Select all' }}
          </label>
          <span v-if="staleSelected.size" class="stale-select-count">{{ staleSelected.size }} selected</span>
        </div>
        <div class="cards-grid">
          <div v-for="l in staleListings" :key="l.url" class="stale-card-wrap">
            <div v-if="translatingId === l.source_listing_id" class="stale-translating-overlay">
              <span class="translation-spinner" style="font-size:1.6rem;color:#A78BFA">⟳</span>
              <span style="font-size:0.75rem;color:#C4B5FD;margin-top:0.3rem">Translating…</span>
            </div>
            <PropertyCard
              :listing="l"
              :is-checked="staleSelected.has(staleKey(l))"
              :style="translatingId === l.source_listing_id ? 'opacity:0.4;pointer-events:none' : ''"
              @toggle-select="toggleOne(l)"
              @updated="onUpdated"
            />
          </div>
        </div>
      </template>
      </template>
    </div>

    <!-- Duplicates -->
    <div class="tools-section">
      <div class="tools-section-header tools-section-toggle" @click="dupOpen = !dupOpen">
        <div>
          <h2>Possible duplicates <span class="section-count" v-if="dupLoaded">({{ duplicates.length }})</span></h2>
          <p>Listings grouped when address, postcode, price, and surface match.</p>
        </div>
        <div class="tools-actions" @click.stop>
          <button class="btn btn-secondary" :disabled="dupLoading" @click="loadDuplicates">
            {{ dupLoading ? 'Checking…' : dupLoaded ? 'Refresh' : 'Show duplicates' }}
          </button>
          <span :class="['section-chevron', { open: dupOpen }]">▼</span>
        </div>
      </div>
      <template v-if="dupOpen">
        <LoadingSpinner v-if="dupLoading" label="Checking duplicates" />
        <div v-else-if="dupError" class="data-error">{{ dupError }}</div>
        <div v-else-if="dupLoaded && !duplicates.length" class="empty">No possible duplicates found.</div>
        <DuplicateGroup v-for="group in duplicates" v-else-if="dupLoaded" :key="group.canonical.url" :group="group" @changed="loadDuplicates" />
      </template>
    </div>

    <!-- History -->
    <div class="tools-section">
      <div class="tools-section-header tools-section-toggle" @click="histOpen = !histOpen">
        <div>
          <h2>Collection history <span class="section-count" v-if="histLoaded">({{ runs.length }})</span></h2>
          <p>Past scraping runs and the listings they saved.</p>
        </div>
        <div class="tools-actions" @click.stop>
          <button class="btn btn-secondary" :disabled="histLoading" @click="loadHistory">
            {{ histLoading ? 'Loading…' : histLoaded ? 'Refresh' : 'Show history' }}
          </button>
          <span :class="['section-chevron', { open: histOpen }]">▼</span>
        </div>
      </div>
      <template v-if="histOpen">
      <LoadingSpinner v-if="histLoading" label="Loading history" />
      <div v-else-if="histLoaded && !runs.length" class="empty">No runs yet.</div>
      <div v-else-if="histLoaded">
        <div v-for="run in runs" :key="run.id" class="run-item">
          <div class="run-header" @click="toggleRun(run.id)">
            <div class="run-status-dot" :style="{ background: statusInfo(run.status).dot }"></div>
            <span class="run-id">Run #{{ run.id }}</span>
            <span class="run-time">{{ fmtTime(run.started_at) }}</span>
            <span class="run-status-text" :style="{ color: statusInfo(run.status).color }">{{ statusInfo(run.status).label }}</span>
            <span :class="['run-chevron', { open: expanded.has(run.id) }]">▼</span>
          </div>
          <div v-if="expanded.has(run.id)" class="run-body">
            <div class="run-sources">
              <div v-for="s in run.sources" :key="s.source" class="run-source-item">
                <div class="source-dot" :style="{ background: s.status === 'ok' ? '#039855' : '#DC2626' }"></div>
                <strong>{{ s.source }}</strong>&nbsp;— {{ s.count }} saved
              </div>
            </div>
            <div v-if="!runListings[run.id]" style="font-size:0.8rem;color:#98A2B3">Loading…</div>
            <div v-else-if="!runListings[run.id].length" class="empty" style="padding:0.5rem 0">Nothing saved in this run.</div>
            <table v-else class="run-table">
              <thead>
                <tr><th>Name / URL</th><th>Price</th><th>Type</th><th>Post</th><th>m²</th><th>Beds</th><th>EPC</th><th>Portal</th></tr>
              </thead>
              <tbody>
                <tr v-for="l in runListings[run.id]" :key="l.url">
                  <td><a :href="l.url" target="_blank">{{ ((l.name || l.address || l.street || l.url || '').slice(0, 40) + (((l.name || l.url || '').length > 40) ? '…' : '')) }}</a></td>
                  <td>{{ fmtPrice(l.price) }}</td>
                  <td>{{ (l.property_type || '').replace(/^\w/, c => c.toUpperCase()) }}</td>
                  <td>{{ l.postcode || '—' }}</td>
                  <td>{{ l.surface_area || '?' }}</td>
                  <td>{{ l.bedrooms || '?' }}</td>
                  <td>{{ l.epc_score || '—' }}</td>
                  <td>{{ l.source || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </template>
    </div>
  </section>
</template>
