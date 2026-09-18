<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api.js'

const { collectionState, appVersion } = defineProps({
  collectionState: { type: Object, required: true },
  appVersion: { type: String, default: '' },
})
const emit = defineEmits(['close-mobile'])

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
  property_types: [],
  max_pages: 5,
  translate_to_english: true,
  include_under_option: true,
  starting_capital: 50000,
  emergency_reserve: 10000,
  monthly_net_income: 4000,
  monthly_debt_payments: 0,
  interest_rate: 3.5,
  loan_term_years: 25,
  debt_service_ratio: 40,
  loan_to_value: 90,
})

const ALL_EPC = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
const ALL_PORTALS = ['immoweb', 'zimmo', 'immoscoop', 'realo', 'immovlan']
const ALL_PROPERTY_TYPES = ['house', 'apartment', 'duplex', 'penthouse', 'ground floor']

const searchSummary = computed(() => {
  const postcode = form.value.postcodes || 'Any area'
  const price = Number(form.value.max_price || 0).toLocaleString('nl-BE')
  return `${postcode} · €${price} max · ${form.value.min_surface_area || 0} m²+ · ${form.value.min_bedrooms || 0} bd+`
})
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
      property_types: [...(c.property_types || [])],
      max_pages: c.max_pages || 5,
      translate_to_english: c.translate_to_english !== false,
      include_under_option: c.include_under_option !== false,
      starting_capital: c.starting_capital ?? 50000,
      emergency_reserve: c.emergency_reserve ?? 10000,
      monthly_net_income: c.monthly_net_income ?? 4000,
      monthly_debt_payments: c.monthly_debt_payments ?? 0,
      interest_rate: (c.interest_rate ?? 0.035) * 100,
      loan_term_years: c.loan_term_years ?? 25,
      debt_service_ratio: (c.debt_service_ratio ?? 0.4) * 100,
      loan_to_value: (c.loan_to_value ?? 0.9) * 100,
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
      property_types: form.value.property_types,
      max_pages: Number(form.value.max_pages) || 5,
      translate_to_english: form.value.translate_to_english,
      include_under_option: form.value.include_under_option,
      starting_capital: Number(form.value.starting_capital) || 0,
      emergency_reserve: Number(form.value.emergency_reserve) || 0,
      monthly_net_income: Number(form.value.monthly_net_income) || 0,
      monthly_debt_payments: Number(form.value.monthly_debt_payments) || 0,
      interest_rate: (Number(form.value.interest_rate) || 0) / 100,
      loan_term_years: Number(form.value.loan_term_years) || 25,
      debt_service_ratio: (Number(form.value.debt_service_ratio) || 0) / 100,
      loan_to_value: (Number(form.value.loan_to_value) || 0) / 100,
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
  await saveConfig()
  try { await api.startRun() } catch {}
}

async function cancelRun() {
  try { await api.cancelRun() } catch {}
}


onMounted(() => {
  loadConfig()
  document.documentElement.classList.toggle('theme-vlaams', theme.value === 'vlaams')
  document.documentElement.setAttribute('data-density', density.value)
})

function loadSectionState(key, def) {
  const val = localStorage.getItem(key)
  return val === null ? def : val === 'true'
}

const searchOpen = ref(loadSectionState('sidebar-section-search-v2', false))
const propertyOpen = ref(loadSectionState('sidebar-section-property', true))
const budgetOpen = ref(loadSectionState('sidebar-section-budget', false))
const searchOptsOpen = ref(loadSectionState('sidebar-section-search-opts', false))

watch(searchOpen, v => localStorage.setItem('sidebar-section-search-v2', v))
watch(propertyOpen, v => localStorage.setItem('sidebar-section-property', v))
watch(budgetOpen, v => localStorage.setItem('sidebar-section-budget', v))
watch(searchOptsOpen, v => localStorage.setItem('sidebar-section-search-opts', v))

const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
const theme = ref(localStorage.getItem('theme') || 'default')
const density = ref(localStorage.getItem('density') || 'spacious')

function toggleDensity() {
  density.value = density.value === 'compact' ? 'spacious' : 'compact'
  localStorage.setItem('density', density.value)
  document.documentElement.setAttribute('data-density', density.value)
}

function expandTo(section) {
  collapsed.value = false
  localStorage.setItem('sidebar-collapsed', 'false')
  if (section === 'search') searchOpen.value = true
}

async function logout() {
  await api.logout().catch(() => {})
  window.location.reload()
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar-collapsed', String(collapsed.value))
}

function toggleTheme() {
  theme.value = theme.value === 'vlaams' ? 'default' : 'vlaams'
  localStorage.setItem('theme', theme.value)
  document.documentElement.classList.toggle('theme-vlaams', theme.value === 'vlaams')
}
</script>

<template>
  <aside :class="['sidebar', { collapsed }]">
    <div class="sidebar-header">
      <div v-if="!collapsed" class="sidebar-title-col">
        <div class="sidebar-title">MAKELAARTJE</div>
        <div class="sidebar-subtitle">Wanneer Vlaming zijn geen grap is</div>
      </div>
      <button class="sidebar-collapse-btn sidebar-mobile-close" type="button" aria-label="Close menu" @click="emit('close-mobile')">×</button>
    </div>

    <div v-if="collapsed" class="sidebar-icon-rail">
      <button class="sidebar-icon-btn" title="Search config" @click="expandTo('search')">S</button>
      <button class="sidebar-icon-btn" :class="{ alive: collectionState.alive }" :title="collectionState.alive ? 'Stop collection' : 'Run collection'" @click="collectionState.alive ? cancelRun() : startRun()">{{ collectionState.alive ? '■' : '▶' }}</button>
    </div>

    <template v-if="!collapsed">

    <div class="sidebar-section">
      <button class="sidebar-section-toggle" :aria-expanded="searchOpen" @click="searchOpen = !searchOpen">
        <span>Search config</span>
        <span class="sidebar-section-summary">{{ searchSummary }}</span>
        <span aria-hidden="true">{{ searchOpen ? '▲' : '▼' }}</span>
      </button>
      <div v-if="searchOpen">
        <label>Postcodes</label>
        <input v-model="form.postcodes" type="text" placeholder="2000, 2018, 2060" />

        <button class="sidebar-subgroup-toggle" @click="propertyOpen = !propertyOpen">
          Property <span>{{ propertyOpen ? '▲' : '▼' }}</span>
        </button>
        <div v-if="propertyOpen" class="sidebar-subgroup-body">
          <label>Type</label>
          <div class="checkbox-group">
            <label v-for="t in ALL_PROPERTY_TYPES" :key="t">
              <input type="checkbox" :value="t" v-model="form.property_types" />
              {{ t }}
            </label>
          </div>

          <label>Min bedrooms</label>
          <input v-model="form.min_bedrooms" type="number" min="0" step="1" />

          <label>Min surface (m²)</label>
          <input v-model="form.min_surface_area" type="number" min="0" step="5" />

          <label>Outdoor</label>
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

          <label>Year range</label>
          <div class="range-inputs">
            <input v-model="form.min_construction_year" type="number" min="1800" max="2100" placeholder="From" />
            <input v-model="form.max_construction_year" type="number" min="1800" max="2100" placeholder="To" />
          </div>
        </div>

        <button class="sidebar-subgroup-toggle" @click="budgetOpen = !budgetOpen">
          Budget & Quality <span>{{ budgetOpen ? '▲' : '▼' }}</span>
        </button>
        <div v-if="budgetOpen" class="sidebar-subgroup-body">
          <label>Max price (€)</label>
          <input v-model="form.max_price" type="number" min="0" step="5000" />

          <label>EPC labels</label>
          <div class="checkbox-group">
            <label v-for="epc in ALL_EPC" :key="epc">
              <input type="checkbox" :value="epc" v-model="form.epc_labels" />
              {{ epc }}
            </label>
          </div>

          <label>Score importance (%)</label>
          <div class="score-weight-grid">
            <label v-for="(label, key) in { price: 'Price', surface_area: 'Surface', bedrooms: 'Bedrooms', epc: 'EPC', completeness: 'Completeness' }" :key="key">
              <span>{{ label }}</span>
              <input v-model.number="form.score_weights[key]" type="number" min="0" max="100" step="5" />
            </label>
          </div>
          <div class="score-weight-total">Total: {{ Object.values(form.score_weights).reduce((sum, value) => sum + Number(value || 0), 0) }}% (must equal 100%)</div>
        </div>

        <button class="sidebar-subgroup-toggle" @click="searchOptsOpen = !searchOptsOpen">
          Search options <span>{{ searchOptsOpen ? '▲' : '▼' }}</span>
        </button>
        <div v-if="searchOptsOpen" class="sidebar-subgroup-body">
          <label>Portals</label>
          <div class="checkbox-group">
            <label v-for="p in ALL_PORTALS" :key="p">
              <input type="checkbox" :value="p" v-model="form.portals" />
              {{ p }}
            </label>
          </div>

          <label>Pages per portal</label>
          <input v-model="form.max_pages" type="number" min="1" step="1" />

          <label>Scraping mode</label>
          <select v-model="form.scrape_mode">
            <option value="all">All listings</option>
            <option value="delta">Delta — new listings only</option>
          </select>

          <label class="checkbox-inline">
            <input type="checkbox" v-model="form.translate_to_english" />
            Translate to English
          </label>

          <label class="checkbox-inline">
            <input type="checkbox" v-model="form.include_under_option" />
            Include under option
          </label>
        </div>

      </div>
    </div>

    <div class="sidebar-section sidebar-action-row-section">
      <div class="sidebar-action-row">
        <button class="sidebar-icon-action save-action" :disabled="saving" @click="saveConfig" :title="saving ? 'Saving…' : 'Save search settings'">
          <svg v-if="!saving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          <span v-else style="font-size:0.75rem">…</span>
        </button>
        <span v-if="saveMsg" class="sidebar-save-msg" :style="{ color: saveMsg.startsWith('Error') ? '#F87171' : '#6EE7B7' }">{{ saveMsg }}</span>

        <template v-if="collectionState.alive">
          <div class="collection-progress" style="margin-right:0.3rem">
            {{ collectionState.cancelling ? 'Cancelling…' : `${collectionState.checked}↑ ${collectionState.saved}✓` }}
          </div>
          <button class="sidebar-icon-action stop-action" @click="cancelRun" title="Stop collection">■</button>
        </template>
        <template v-else>
          <div v-if="collectionState.status && collectionState.status !== 'running'" class="collection-status-inline" style="margin-right:0.3rem">
            <span v-if="collectionState.status === 'ok' || collectionState.status === 'partial'" style="color:#6EE7B7">✓ {{ collectionState.saved }}</span>
            <span v-else-if="collectionState.status === 'cancelled'" style="color:#94A3B8">—</span>
            <span v-else-if="collectionState.status === 'error'" style="color:#F87171">!</span>
          </div>
          <button class="sidebar-icon-action run-action" @click="startRun" title="Run collection">▶</button>
        </template>
      </div>
      <div v-if="collectionState.translating" class="translation-progress" style="margin-top:0.35rem">
        <div class="translation-progress-label">
          <span class="translation-spinner">⟳</span>
          Translating {{ collectionState.translation_done }}/{{ collectionState.translation_total }}
        </div>
        <div class="translation-progress-bar">
          <div class="translation-progress-fill" :style="{ width: collectionState.translation_total ? Math.round((collectionState.translation_done / collectionState.translation_total) * 100) + '%' : '0%' }" />
        </div>
        <div v-if="collectionState.translation_current" class="translation-current-item">
          <span class="translation-current-id">#{{ collectionState.translation_current }}</span>
          <span v-if="collectionState.translation_current_address" class="translation-current-addr">{{ collectionState.translation_current_address }}</span>
        </div>
      </div>
    </div>

    <div class="sidebar-section sidebar-theme-section">
      <div class="sidebar-flag-wrap">
        <button :class="['sidebar-theme-btn', { active: theme === 'vlaams' }]" type="button" :title="theme === 'vlaams' ? 'Switch to default theme' : 'Switch to Vlaams theme'" @click="toggleTheme">
          <img src="https://p7.hiclipart.com/preview/674/441/226/flemish-region-the-lion-of-flanders-flag-of-flanders-de-vlaamse-leeuw-t-shirt.jpg" alt="Vlaams theme" class="sidebar-theme-icon" />
        </button>
        <span v-if="appVersion" class="sidebar-version-over">v{{ appVersion }}</span>
      </div>
      <button class="sidebar-logout-btn" type="button" title="Sign out" @click="logout">↪</button>
      <button class="sidebar-collapse-btn" :title="collapsed ? 'Expand' : 'Collapse'" @click="toggleCollapse">{{ collapsed ? '›' : '‹' }}</button>
    </div>
    </template>
  </aside>
</template>
