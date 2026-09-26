<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api.js'

defineOptions({ name: 'AdminSettings' })

const PORTALS = ['immoweb', 'zimmo', 'immoscoop', 'realo', 'immovlan']
const EPC_LABELS = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
const PROPERTY_TYPES = ['house', 'apartment', 'duplex', 'penthouse', 'ground floor']
const DEFAULT_WEIGHTS = { price: 30, surface_area: 25, bedrooms: 15, epc: 20, completeness: 10 }
const DEFAULT_CONFIG = {
  postcodes: [], max_price: 385000, min_surface_area: 80, min_bedrooms: 2,
  outdoor_features: [], building_age: 'any', min_construction_year: null,
  max_construction_year: null, scrape_mode: 'all', score_weights: DEFAULT_WEIGHTS,
  epc_labels: [], portals: [], property_types: [], max_pages: 5,
  translate_to_english: true, include_under_option: true,
}

const loading = ref(true)
const loadError = ref('')
const config = ref({ ...DEFAULT_CONFIG })
const settings = ref({
  ollama: { base_url: 'http://localhost:11434', model: '' },
  database: { mode: 'local', host: '127.0.0.1', port: 5432, dbname: 'immotool', user: 'immotool', sslmode: 'prefer', sslrootcert: '' },
})
const activeJobs = ref(false)
const passwordConfigured = ref(false)
const newPassword = ref('')
const systemStatus = ref({ kind: '', message: '' })
const configStatus = ref({ kind: '', message: '' })
const ollamaTest = ref({ kind: '', message: '' })
const databaseTest = ref({ kind: '', message: '' })
const savingSystem = ref(false)
const testingOllama = ref(false)
const testingDatabase = ref(false)
let systemTimer = null
let configTimer = null
let initialized = false
let systemSaveQueue = Promise.resolve()
let configSaveQueue = Promise.resolve()

const weightTotal = computed(() => Object.values(config.value.score_weights || {}).reduce((sum, value) => sum + Number(value || 0), 0))
const databaseIsRemote = computed(() => settings.value.database.mode === 'remote')
const systemValidation = computed(() => {
  const db = settings.value.database
  if (!settings.value.ollama.base_url || !settings.value.ollama.model) return 'Enter an Ollama endpoint and model.'
  try { new URL(settings.value.ollama.base_url) } catch { return 'Enter a valid Ollama endpoint URL.' }
  if (!db.host || !db.dbname || !db.user || !Number.isInteger(Number(db.port)) || Number(db.port) < 1 || Number(db.port) > 65535) {
    return 'Enter a database host, name, user, and valid port.'
  }
  if (db.mode === 'remote' && (db.host !== 'kodisrv' || db.dbname !== 'immotool' || db.user !== 'immotool' || db.sslmode !== 'verify-full' || !db.sslrootcert)) {
    return 'Remote mode requires host kodisrv, database and user immotool, verify-full SSL, and a root certificate path.'
  }
  return ''
})

function normalizeConfig(saved) {
  const result = { ...DEFAULT_CONFIG, ...saved }
  result.postcodes = (saved.postcodes || []).join(', ')
  result.score_weights = { ...DEFAULT_WEIGHTS, ...(saved.score_weights || {}) }
  result.portals = [...(saved.portals || [])]
  result.epc_labels = [...(saved.epc_labels || [])]
  result.property_types = [...(saved.property_types || [])]
  result.outdoor_features = [...(saved.outdoor_features || [])]
  return result
}

function normalizeSettings(saved) {
  return {
    ollama: { base_url: saved.ollama?.base_url || '', model: saved.ollama?.model || '' },
    database: {
      mode: saved.database?.mode || 'local',
      host: saved.database?.host || '',
      port: saved.database?.port ?? 5432,
      dbname: saved.database?.dbname || '',
      user: saved.database?.user || '',
      sslmode: saved.database?.sslmode || 'prefer',
      sslrootcert: saved.database?.sslrootcert || '',
    },
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [savedSettings, savedConfig] = await Promise.all([api.getSettings(), api.getConfig()])
    settings.value = normalizeSettings(savedSettings)
    activeJobs.value = Boolean(savedSettings.active_jobs)
    passwordConfigured.value = Boolean(savedSettings.database?.password_configured)
    config.value = normalizeConfig(savedConfig)
    await nextTick()
    initialized = true
  } catch (error) {
    loadError.value = error.message || 'Could not load settings.'
  } finally {
    loading.value = false
  }
}

function databasePayload() {
  return { ...settings.value.database, password: newPassword.value }
}

function saveSystemSettings() {
  if (!initialized || loading.value) return
  clearTimeout(systemTimer)
  if (systemValidation.value) {
    systemStatus.value = { kind: 'error', message: systemValidation.value }
    return
  }
  systemStatus.value = { kind: 'pending', message: 'Applying changes…' }
  systemTimer = setTimeout(() => {
    const payload = {
      ollama: { ...settings.value.ollama },
      database: databasePayload(),
    }
    systemSaveQueue = systemSaveQueue.then(async () => {
      savingSystem.value = true
      try {
        const result = await api.updateSettings(payload)
        if (payload.database.password) passwordConfigured.value = true
        newPassword.value = ''
        systemStatus.value = {
          kind: 'success',
          message: result.database_changed ? 'Changes applied immediately. Database connection updated.' : 'Changes applied immediately.',
        }
      } catch (error) {
        systemStatus.value = { kind: 'error', message: error.message || 'Could not apply settings.' }
      } finally {
        savingSystem.value = false
      }
    })
  }, 550)
}

function configPayload() {
  return {
    ...config.value,
    postcodes: String(config.value.postcodes || '').split(',').map(value => value.trim()).filter(Boolean),
    max_price: Number(config.value.max_price) || null,
    min_surface_area: Number(config.value.min_surface_area) || null,
    min_bedrooms: Number(config.value.min_bedrooms) || null,
    max_pages: Number(config.value.max_pages) || 1,
    min_construction_year: Number(config.value.min_construction_year) || null,
    max_construction_year: Number(config.value.max_construction_year) || null,
  }
}

function saveConfig() {
  if (!initialized || loading.value) return
  clearTimeout(configTimer)
  if (weightTotal.value !== 100) {
    configStatus.value = { kind: 'error', message: 'Score weights must total 100% before they can be applied.' }
    return
  }
  configStatus.value = { kind: 'pending', message: 'Applying changes…' }
  configTimer = setTimeout(() => {
    const payload = configPayload()
    configSaveQueue = configSaveQueue.then(async () => {
      try {
        await api.updateConfig(payload)
        configStatus.value = { kind: 'success', message: 'Changes applied.' }
      } catch (error) {
        configStatus.value = { kind: 'error', message: error.message || 'Could not save general settings.' }
      }
    })
  }, 550)
}

async function checkOllama() {
  if (systemValidation.value) {
    ollamaTest.value = { kind: 'error', message: systemValidation.value }
    return
  }
  testingOllama.value = true
  ollamaTest.value = { kind: 'pending', message: 'Checking Ollama…' }
  try {
    const result = await api.testOllama({ ...settings.value.ollama })
    ollamaTest.value = result.model_available
      ? { kind: 'success', message: result.message || 'Ollama connection successful.' }
      : { kind: 'error', message: `Connected, but model “${settings.value.ollama.model}” is not installed.` }
  } catch (error) {
    ollamaTest.value = { kind: 'error', message: error.message || 'Ollama connection failed.' }
  } finally {
    testingOllama.value = false
  }
}

async function checkDatabase() {
  if (systemValidation.value) {
    databaseTest.value = { kind: 'error', message: systemValidation.value }
    return
  }
  testingDatabase.value = true
  databaseTest.value = { kind: 'pending', message: 'Checking database…' }
  try {
    const result = await api.testDatabase(databasePayload())
    databaseTest.value = { kind: 'success', message: result.message || 'Database connection successful.' }
  } catch (error) {
    databaseTest.value = { kind: 'error', message: error.message || 'Database connection failed.' }
  } finally {
    testingDatabase.value = false
  }
}

watch(settings, saveSystemSettings, { deep: true })
watch(config, saveConfig, { deep: true })

onMounted(load)
onBeforeUnmount(() => {
  clearTimeout(systemTimer)
  clearTimeout(configTimer)
})
</script>

<template>
  <main class="settings-view">
    <header class="settings-header">
      <div>
        <p class="settings-eyebrow">ADMINISTRATION</p>
        <h1>Settings</h1>
        <p class="settings-intro">Service connections and the defaults used for new searches.</p>
      </div>
      <span v-if="activeJobs" class="settings-job-badge">Collection running</span>
    </header>

    <div v-if="loading" class="settings-message">Loading settings…</div>
    <div v-else-if="loadError" class="settings-message settings-error" role="alert">{{ loadError }} <button class="btn btn-secondary btn-sm" @click="load">Retry</button></div>
    <template v-else>
      <section class="settings-card">
        <div class="settings-card-heading">
          <div><h2>Ollama</h2><p>Choose the local language model service used for listing analysis.</p></div>
          <button class="btn btn-secondary btn-sm" :disabled="testingOllama || savingSystem || Boolean(systemValidation)" @click="checkOllama">{{ testingOllama ? 'Testing…' : 'Test connection' }}</button>
        </div>
        <div class="settings-grid">
          <label class="settings-field settings-field-wide"><span>Endpoint</span><input v-model.trim="settings.ollama.base_url" type="url" placeholder="http://localhost:11434" autocomplete="url" /></label>
          <label class="settings-field"><span>Model</span><input v-model.trim="settings.ollama.model" type="text" placeholder="llama3.1" /></label>
        </div>
        <p v-if="ollamaTest.message" :class="['settings-status', `is-${ollamaTest.kind}`]" role="status">{{ ollamaTest.message }}</p>
        <p v-else-if="systemStatus.message" :class="['settings-status', `is-${systemStatus.kind}`]" role="status">{{ systemStatus.message }}</p>
        <p v-if="systemValidation" class="settings-status is-error" role="status">{{ systemValidation }}</p>
      </section>

      <section class="settings-card">
        <div class="settings-card-heading">
          <div><h2>Database</h2><p>Connection changes are applied immediately. Password is never returned to the browser.</p></div>
          <button class="btn btn-secondary btn-sm" :disabled="activeJobs || testingDatabase || savingSystem || Boolean(systemValidation)" @click="checkDatabase">{{ testingDatabase ? 'Testing…' : 'Test connection' }}</button>
        </div>
        <div v-if="activeJobs" class="settings-notice">Database settings are locked while a collection is running.</div>
        <div class="settings-grid">
          <label class="settings-field"><span>Connection</span><select v-model="settings.database.mode" :disabled="activeJobs"><option value="local">Local PostgreSQL</option><option value="remote">Remote PostgreSQL</option></select></label>
          <label class="settings-field"><span>Host</span><input v-model.trim="settings.database.host" type="text" placeholder="127.0.0.1" :disabled="activeJobs" /></label>
          <label class="settings-field"><span>Port</span><input v-model.number="settings.database.port" type="number" min="1" max="65535" step="1" :disabled="activeJobs" /></label>
          <label class="settings-field"><span>Database</span><input v-model.trim="settings.database.dbname" type="text" :disabled="activeJobs" /></label>
          <label class="settings-field"><span>User</span><input v-model.trim="settings.database.user" type="text" :disabled="activeJobs" autocomplete="username" /></label>
          <label class="settings-field"><span>Password</span><input v-model="newPassword" type="password" :placeholder="passwordConfigured ? 'Configured — leave blank to keep' : 'Enter database password'" :disabled="activeJobs" autocomplete="new-password" @change="saveSystemSettings" /></label>
          <label class="settings-field"><span>SSL mode</span><select v-model="settings.database.sslmode" :disabled="activeJobs"><option value="disable">Disable</option><option value="prefer">Prefer</option><option value="require">Require</option><option value="verify-ca">Verify CA</option><option value="verify-full">Verify full</option></select></label>
          <label class="settings-field settings-field-wide"><span>SSL root certificate path</span><input v-model.trim="settings.database.sslrootcert" type="text" placeholder="/path/to/root.crt" :disabled="activeJobs || !databaseIsRemote" /></label>
        </div>
        <p v-if="databaseIsRemote" class="settings-hint">Remote mode requires the configured production host, database, user, SSL mode, and certificate path.</p>
        <p v-if="databaseTest.message" :class="['settings-status', `is-${databaseTest.kind}`]" role="status">{{ databaseTest.message }}</p>
        <p v-else-if="systemStatus.message" :class="['settings-status', `is-${systemStatus.kind}`]" role="status">{{ systemStatus.message }}</p>
      </section>

      <section class="settings-card">
        <div class="settings-card-heading">
          <div><h2>General</h2><p>These defaults are applied to future searches and update as soon as you change them.</p></div>
        </div>
        <div class="settings-subsection">
          <h3>Search area and property</h3>
          <div class="settings-grid">
            <label class="settings-field settings-field-wide"><span>Postcodes</span><input v-model="config.postcodes" type="text" placeholder="2000, 2018, 2060" /></label>
            <label class="settings-field"><span>Maximum price (€)</span><input v-model.number="config.max_price" type="number" min="0" step="5000" /></label>
            <label class="settings-field"><span>Minimum surface (m²)</span><input v-model.number="config.min_surface_area" type="number" min="0" step="5" /></label>
            <label class="settings-field"><span>Minimum bedrooms</span><input v-model.number="config.min_bedrooms" type="number" min="0" step="1" /></label>
            <label class="settings-field"><span>Building age</span><select v-model="config.building_age"><option value="any">Any</option><option value="project">New project</option><option value="old">Existing / old</option></select></label>
            <div class="settings-field settings-field-wide"><span>Property types</span><div class="settings-checks"><label v-for="type in PROPERTY_TYPES" :key="type"><input v-model="config.property_types" type="checkbox" :value="type" />{{ type }}</label></div></div>
            <div class="settings-field settings-field-wide"><span>Energy labels</span><div class="settings-checks"><label v-for="epc in EPC_LABELS" :key="epc"><input v-model="config.epc_labels" type="checkbox" :value="epc" />{{ epc }}</label></div></div>
            <div class="settings-field settings-field-wide"><span>Outdoor features</span><div class="settings-checks"><label><input v-model="config.outdoor_features" type="checkbox" value="terrace" />Terrace</label><label><input v-model="config.outdoor_features" type="checkbox" value="garden" />Garden</label></div></div>
          </div>
        </div>
        <div class="settings-subsection">
          <h3>Collection and translation</h3>
          <div class="settings-grid">
            <div class="settings-field settings-field-wide"><span>Portals</span><div class="settings-checks"><label v-for="portal in PORTALS" :key="portal"><input v-model="config.portals" type="checkbox" :value="portal" />{{ portal }}</label></div></div>
            <label class="settings-field"><span>Pages per portal</span><input v-model.number="config.max_pages" type="number" min="1" step="1" /></label>
            <label class="settings-field"><span>Scraping mode</span><select v-model="config.scrape_mode"><option value="all">All listings</option><option value="delta">New listings only</option></select></label>
            <label class="settings-toggle"><input v-model="config.translate_to_english" type="checkbox" /><span>Translate listing descriptions to English</span></label>
            <label class="settings-toggle"><input v-model="config.include_under_option" type="checkbox" /><span>Include listings under option</span></label>
          </div>
        </div>
        <div class="settings-subsection">
          <h3>Score importance</h3>
          <div class="settings-grid">
            <label v-for="(label, key) in { price: 'Price (lower is better)', surface_area: 'Surface', bedrooms: 'Bedrooms', epc: 'EPC', completeness: 'Completeness' }" :key="key" class="settings-field"><span>{{ label }} (%)</span><input v-model.number="config.score_weights[key]" type="number" min="0" max="100" step="5" /></label>
          </div>
          <p :class="['settings-hint', { 'settings-error': weightTotal !== 100 }]">Weight total: {{ weightTotal }}% (should equal 100%)</p>
        </div>
        <p v-if="configStatus.message" :class="['settings-status', `is-${configStatus.kind}`]" role="status">{{ configStatus.message }}</p>
      </section>
    </template>
  </main>
</template>
