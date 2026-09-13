<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'

const config = ref(null)
const saving = ref(false)
const saveMsg = ref('')

const form = ref({
  postcodes: '',
  max_price: 385000,
  min_surface_area: 80,
  min_bedrooms: 2,
  outdoor_features: [],
  building_age: 'any',
  min_construction_year: null,
  max_construction_year: null,
  scrape_mode: 'all',
  score_weights: { price: 30, surface_area: 25, bedrooms: 15, epc: 20, completeness: 10 },
  epc_labels: [],
  portals: [],
  max_pages: 5,
})

const ALL_EPC = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
const ALL_PORTALS = ['immoweb', 'zimmo', 'immoscoop', 'realo', 'immovlan']

const collectionState = ref({ alive: false, checked: 0, saved: 0, portal: '', status: null, error: null, cancelling: false })
let sse = null

function connectSSE() {
  if (sse) sse.close()
  sse = new EventSource('/api/runs/stream')
  sse.onmessage = (e) => {
    const d = JSON.parse(e.data)
    collectionState.value = { ...collectionState.value, ...d }
  }
  sse.onerror = () => {
    setTimeout(connectSSE, 3000)
  }
}

async function loadConfig() {
  try {
    const c = await api.getConfig()
    config.value = c
    form.value = {
      postcodes: (c.postcodes || []).join(', '),
      max_price: c.max_price || 385000,
      min_surface_area: c.min_surface_area || 80,
      min_bedrooms: c.min_bedrooms || 2,
      outdoor_features: [...(c.outdoor_features || [])],
      building_age: c.building_age || 'any',
      min_construction_year: c.min_construction_year || null,
      max_construction_year: c.max_construction_year || null,
      scrape_mode: c.scrape_mode || 'all',
      score_weights: { ...form.value.score_weights, ...(c.score_weights || {}) },
      epc_labels: [...(c.epc_labels || [])],
      portals: [...(c.portals || [])],
      max_pages: c.max_pages || 5,
    }
  } catch {}
}

async function saveConfig() {
  saving.value = true
  saveMsg.value = ''
  try {
    await api.updateConfig({
      postcodes: form.value.postcodes.split(',').map(s => s.trim()).filter(Boolean),
      max_price: Number(form.value.max_price) || null,
      min_surface_area: Number(form.value.min_surface_area) || null,
      min_bedrooms: Number(form.value.min_bedrooms) || null,
      outdoor_features: form.value.outdoor_features,
      building_age: form.value.building_age,
      min_construction_year: Number(form.value.min_construction_year) || null,
      max_construction_year: Number(form.value.max_construction_year) || null,
      scrape_mode: form.value.scrape_mode,
      score_weights: form.value.score_weights,
      epc_labels: form.value.epc_labels,
      portals: form.value.portals,
      max_pages: Number(form.value.max_pages) || 5,
    })
    saveMsg.value = 'Saved'
    window.dispatchEvent(new CustomEvent('search-config-updated'))
    setTimeout(() => { saveMsg.value = '' }, 2000)
  } catch (err) {
    saveMsg.value = 'Error: ' + err.message
  }
  saving.value = false
}

async function startRun() {
  try { await api.startRun() } catch {}
}

async function cancelRun() {
  try { await api.cancelRun() } catch {}
}

onMounted(() => {
  loadConfig()
  connectSSE()
})

onUnmounted(() => {
  if (sse) sse.close()
})

const searchOpen = ref(true)
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">Immowbot</div>
      <div class="sidebar-subtitle">Antwerp buyer</div>
    </div>

    <div class="sidebar-section">
      <button class="sidebar-label" style="background:none;border:none;cursor:pointer;text-align:left;width:100%;display:flex;justify-content:space-between;align-items:center" @click="searchOpen = !searchOpen">
        <span>Search config</span>
        <span style="font-size:0.65rem">{{ searchOpen ? '▲' : '▼' }}</span>
      </button>
      <div v-if="searchOpen">
        <label>Postcodes</label>
        <input v-model="form.postcodes" type="text" placeholder="2000, 2018, 2060" />

        <label>Max price (€)</label>
        <input v-model="form.max_price" type="number" min="0" step="5000" />

        <label>Min surface (m²)</label>
        <input v-model="form.min_surface_area" type="number" min="0" step="5" />

        <label>Min bedrooms</label>
        <input v-model="form.min_bedrooms" type="number" min="0" step="1" />

        <label>Outdoor features</label>
        <div class="checkbox-group">
          <label><input v-model="form.outdoor_features" type="checkbox" value="terrace" /> Terrace</label>
          <label><input v-model="form.outdoor_features" type="checkbox" value="garden" /> Garden</label>
        </div>

        <label>Building age</label>
        <select v-model="form.building_age">
          <option value="any">Any</option>
          <option value="project">New project</option>
          <option value="old">Existing / old</option>
        </select>

        <label>Construction year range</label>
        <div class="range-inputs">
          <input v-model="form.min_construction_year" type="number" min="1800" max="2100" placeholder="From" />
          <input v-model="form.max_construction_year" type="number" min="1800" max="2100" placeholder="To" />
        </div>

        <label>Scraping mode</label>
        <select v-model="form.scrape_mode">
          <option value="all">All listings</option>
          <option value="delta">Delta — new listings only</option>
        </select>

        <label>Score importance (%)</label>
        <div class="score-weight-grid">
          <label v-for="(label, key) in { price: 'Price', surface_area: 'Surface', bedrooms: 'Bedrooms', epc: 'EPC', completeness: 'Completeness' }" :key="key">
            <span>{{ label }}</span>
            <input v-model.number="form.score_weights[key]" type="number" min="0" max="100" step="5" />
          </label>
        </div>
        <div class="score-weight-total">Total: {{ Object.values(form.score_weights).reduce((sum, value) => sum + Number(value || 0), 0) }}% (must equal 100%)</div>

        <label>EPC labels</label>
        <div class="checkbox-group">
          <label v-for="epc in ALL_EPC" :key="epc">
            <input type="checkbox" :value="epc" v-model="form.epc_labels" />
            {{ epc }}
          </label>
        </div>

        <label>Portals</label>
        <div class="checkbox-group">
          <label v-for="p in ALL_PORTALS" :key="p">
            <input type="checkbox" :value="p" v-model="form.portals" />
            {{ p }}
          </label>
        </div>

        <label>Pages per portal</label>
        <input v-model="form.max_pages" type="number" min="1" step="1" />

        <button class="btn btn-sidebar-primary" :disabled="saving" @click="saveConfig">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <div v-if="saveMsg" style="font-size:0.72rem;margin-top:0.4rem" :style="{ color: saveMsg.startsWith('Error') ? '#F87171' : '#6EE7B7' }">{{ saveMsg }}</div>
      </div>
    </div>

    <div class="sidebar-section">
      <span class="sidebar-label">Collection</span>

      <div v-if="collectionState.alive">
        <div class="collection-progress">
          {{ collectionState.cancelling ? 'Cancelling…' : `Checked ${collectionState.checked} · Saved ${collectionState.saved}` }}
          <span v-if="collectionState.portal" style="color:#6366F1"> · {{ collectionState.portal }}</span>
        </div>
        <button class="btn btn-sidebar-secondary" @click="cancelRun">Stop</button>
      </div>

      <div v-else>
        <div v-if="collectionState.status && collectionState.status !== 'running'" style="margin-bottom:0.5rem">
          <div v-if="collectionState.status === 'ok' || collectionState.status === 'partial'" class="collection-status done">
            Done — {{ collectionState.saved }} saved
          </div>
          <div v-else-if="collectionState.status === 'cancelled'" class="collection-status cancelled">
            Cancelled
          </div>
          <div v-else-if="collectionState.status === 'error'" class="collection-status error">
            Error: {{ collectionState.error }}
          </div>
        </div>
        <button class="btn btn-sidebar-primary" @click="startRun">Run collection</button>
      </div>
    </div>
  </aside>
</template>
