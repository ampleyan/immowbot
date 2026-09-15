<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from './api.js'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import Alerts from './views/Alerts.vue'
import History from './views/History.vue'
import Lists from './views/Lists.vue'
import Pipeline from './views/Pipeline.vue'
import Duplicates from './views/Duplicates.vue'

const tab = ref('listings')
const authenticated = ref(false)
const checkingAuth = ref(true)
const alertCount = ref(0)
const appVersion = ref('')

async function loadAlertCount() {
  try {
    const alerts = await api.getAlerts()
    alertCount.value = alerts.filter(a => !a.read_at).length
  } catch {}
}

const registerMatch = window.location.pathname.match(/^\/register\/([^/]+)$/)
const inviteToken = registerMatch ? registerMatch[1] : null
const mobileMenuOpen = ref(false)
const collectionState = ref({ alive: false, checked: 0, saved: 0, portal: '', status: null, error: null, cancelling: false })
let progressStream = null

function connectProgressStream() {
  if (progressStream) progressStream.close()
  progressStream = new EventSource('/api/runs/stream')
  progressStream.onmessage = (event) => {
    collectionState.value = { ...collectionState.value, ...JSON.parse(event.data) }
  }
  progressStream.onerror = () => {
    setTimeout(connectProgressStream, 3000)
  }
}

function switchTab(t) {
  tab.value = t
  mobileMenuOpen.value = false
}

watch(collectionState, (state, prev) => {
  if (prev.alive && !state.alive) loadAlertCount()
})

onMounted(async () => {
  try {
    await api.me()
    authenticated.value = true
    connectProgressStream()
    loadAlertCount()
    api.health().then(h => { appVersion.value = h.version || '' }).catch(() => {})
  } catch {}
  checkingAuth.value = false
})

onUnmounted(() => {
  if (progressStream) progressStream.close()
})
</script>

<template>
  <Register v-if="inviteToken" :token="inviteToken" @authenticated="authenticated = true; checkingAuth = false" />
  <Login v-else-if="!checkingAuth && !authenticated" @authenticated="authenticated = true" />
  <div v-else-if="authenticated" :class="['app', { 'sidebar-open': mobileMenuOpen }]">
    <div class="mobile-backdrop" @click="mobileMenuOpen = false" />
    <Sidebar :collection-state="collectionState" :app-version="appVersion" @close-mobile="mobileMenuOpen = false" />
    <div class="main">
      <nav class="tabs">
        <button class="mobile-menu-btn" type="button" aria-label="Open settings" @click="mobileMenuOpen = !mobileMenuOpen">☰</button>
        <button :class="['tab-btn', { active: tab === 'listings' }]" @click="switchTab('listings')">Active</button>
        <button :class="['tab-btn', { active: tab === 'alerts' }]" @click="switchTab('alerts')">
          Alerts<span v-if="alertCount" class="tab-alert-count">{{ alertCount }}</span>
        </button>
        <button :class="['tab-btn', { active: tab === 'lists' }]" @click="switchTab('lists')">Lists</button>
        <button :class="['tab-btn', { active: tab === 'pipeline' }]" @click="switchTab('pipeline')">Pipeline</button>
        <button :class="['tab-btn', { active: tab === 'duplicates' }]" @click="switchTab('duplicates')">Dupe</button>
        <button :class="['tab-btn', { active: tab === 'history' }]" @click="switchTab('history')">History</button>
      </nav>
      <div class="tab-content">
        <Listings v-if="tab === 'listings'" :collection-state="collectionState" />
        <Alerts v-else-if="tab === 'alerts'" @alerts-cleared="alertCount = 0" />
        <History v-else-if="tab === 'history'" />
        <Lists v-else-if="tab === 'lists'" />
        <Pipeline v-else-if="tab === 'pipeline'" />
        <Duplicates v-else />
      </div>
    </div>
  </div>
</template>
