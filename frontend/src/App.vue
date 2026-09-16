<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from './api.js'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import Alerts from './views/Alerts.vue'
import Lists from './views/Lists.vue'
import Pipeline from './views/Pipeline.vue'
import Duplicates from './views/Duplicates.vue'
import HelpModal from './components/HelpModal.vue'

const route = useRoute()
const router = useRouter()

const tab = computed(() => {
  const p = route.path.replace(/^\//, '') || 'active'
  return p === 'active' ? 'listings' : p
})

const showHelp = ref(false)
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

const inviteToken = computed(() => route.name === 'register' ? route.params.token : null)
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
  const path = t === 'listings' ? '/active' : `/${t}`
  router.push(path)
  mobileMenuOpen.value = false
}

let alertInterval = null

watch(collectionState, (state, prev) => {
  if (prev.alive && !state.alive) loadAlertCount()
})

watch(() => route.path, (path, prev) => {
  if (prev === '/alerts') loadAlertCount()
})

onMounted(async () => {
  try {
    await api.me()
    authenticated.value = true
    connectProgressStream()
    loadAlertCount()
    alertInterval = setInterval(loadAlertCount, 60000)
    api.health().then(h => { appVersion.value = h.version || '' }).catch(() => {})
  } catch {}
  checkingAuth.value = false
})

onUnmounted(() => {
  if (progressStream) progressStream.close()
  if (alertInterval) clearInterval(alertInterval)
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
        <button :class="['tab-btn', { active: tab === 'tools' }]" @click="switchTab('tools')">Tools</button>
        <button class="help-btn" type="button" @click="showHelp = true" title="Help & What's New">?</button>
      </nav>
      <HelpModal v-if="showHelp" :version="appVersion" @close="showHelp = false" />
      <div class="tab-content">
        <Listings v-if="tab === 'listings'" :collection-state="collectionState" />
        <Alerts v-else-if="tab === 'alerts'" @alerts-cleared="alertCount = 0" />
        <Lists v-else-if="tab === 'lists'" />
        <Pipeline v-else-if="tab === 'pipeline'" />
        <Duplicates v-else :collection-state="collectionState" />
      </div>
    </div>
  </div>
</template>
