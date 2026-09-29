<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from './api.js'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import HomeView from './views/HomeView.vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import Alerts from './views/Alerts.vue'
import Lists from './views/Lists.vue'
import Pipeline from './views/Pipeline.vue'
import HelpModal from './components/HelpModal.vue'
import Manage from './views/Manage.vue'

const route = useRoute()
const router = useRouter()

const tab = computed(() => {
  const p = route.path.replace(/^\//, '') || 'home'
  if (p === 'active') return 'listings'
  if (p === 'tools' || p === 'settings') return 'manage'
  return p
})
const activeNavTab = computed(() => tab.value === 'listings' && route.query.triage === 'new' ? 'new' : tab.value)

const showHelp = ref(false)
const authenticated = ref(false)
const isAdmin = ref(false)
const checkingAuth = ref(true)
const newPropertyCount = ref(0)
const appVersion = ref('')

async function loadNewPropertyCount() {
  try {
    const summary = await api.getBriefSummary()
    newPropertyCount.value = summary.new_count || 0
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
  const path = t === 'listings' ? '/active' : t === 'new' ? '/active?triage=new' : `/${t}`
  router.push(path)
  mobileMenuOpen.value = false
}

async function markAuthenticated() {
  try {
    const user = await api.me()
    isAdmin.value = Boolean(user.is_admin)
  } catch {
    isAdmin.value = false
  }
  authenticated.value = true
}

let alertInterval = null

watch(collectionState, (state, prev) => {
  if (prev.alive && !state.alive) loadNewPropertyCount()
})

watch([() => route.path, isAdmin, authenticated], ([path, admin, loggedIn]) => {
  if (path === '/settings' && loggedIn && !admin) router.replace('/home')
})

onMounted(async () => {
  try {
    const user = await api.me()
    authenticated.value = true
    isAdmin.value = Boolean(user.is_admin)
    connectProgressStream()
    loadNewPropertyCount()
    alertInterval = setInterval(loadNewPropertyCount, 60000)
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
  <Register v-if="inviteToken" :token="inviteToken" @authenticated="markAuthenticated(); checkingAuth = false" />
  <Login v-else-if="!checkingAuth && !authenticated" @authenticated="markAuthenticated" />
  <div v-else-if="authenticated" :class="['app', { 'sidebar-open': mobileMenuOpen }]">
    <div class="mobile-backdrop" @click="mobileMenuOpen = false" />
    <Sidebar :collection-state="collectionState" :app-version="appVersion" @close-mobile="mobileMenuOpen = false" />
    <div class="main">
      <a class="skip-link" href="#main-content">Skip to content</a>
      <nav class="tabs" aria-label="Main navigation">
        <button class="mobile-menu-btn" type="button" aria-label="Open settings" @click="mobileMenuOpen = !mobileMenuOpen">☰</button>
        <button :class="['tab-btn', { active: activeNavTab === 'home' }]" @click="switchTab('home')">Brief</button>
        <button :class="['tab-btn', { active: activeNavTab === 'listings' }]" @click="switchTab('listings')">Active</button>
        <button :class="['tab-btn', { active: activeNavTab === 'new' }]" @click="switchTab('new')">New (+{{ newPropertyCount }})</button>
        <button :class="['tab-btn', { active: activeNavTab === 'lists' }]" @click="switchTab('lists')">Lists</button>
        <button :class="['tab-btn', { active: activeNavTab === 'pipeline' }]" @click="switchTab('pipeline')">Pipeline</button>
        <button :class="['tab-btn', { active: activeNavTab === 'manage' }]" @click="switchTab('manage')">Manage</button>
        <button class="help-btn" type="button" @click="showHelp = true" title="Help & What's New">?</button>
      </nav>
      <HelpModal v-if="showHelp" :version="appVersion" @close="showHelp = false" />
      <main id="main-content" class="tab-content" tabindex="-1">
        <HomeView v-if="tab === 'home'" :collection-state="collectionState" />
        <Listings v-else-if="tab === 'listings'" :collection-state="collectionState" :triage-filter="typeof route.query.triage === 'string' ? route.query.triage : 'all'" />
        <Alerts v-else-if="tab === 'alerts'" />
        <Lists v-else-if="tab === 'lists'" />
        <Pipeline v-else-if="tab === 'pipeline'" />
        <Manage v-else-if="tab === 'manage'" :collection-state="collectionState" :is-admin="isAdmin" :initial-section="route.path === '/settings' || route.query.section === 'settings' ? 'settings' : 'tools'" />
      </main>
    </div>
  </div>
</template>
