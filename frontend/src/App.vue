<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { api } from './api.js'
import Login from './components/Login.vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import History from './views/History.vue'
import Lists from './views/Lists.vue'
import Pipeline from './views/Pipeline.vue'
import Duplicates from './views/Duplicates.vue'

const tab = ref('listings')
const authenticated = ref(false)
const checkingAuth = ref(true)
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

onMounted(async () => {
  try {
    await api.me()
    authenticated.value = true
    connectProgressStream()
  } catch {}
  checkingAuth.value = false
})

onUnmounted(() => {
  if (progressStream) progressStream.close()
})
</script>

<template>
  <Login v-if="!checkingAuth && !authenticated" @authenticated="authenticated = true" />
  <div v-else-if="authenticated" class="app">
    <Sidebar :collection-state="collectionState" />
    <div class="main">
      <nav class="tabs">
        <button :class="['tab-btn', { active: tab === 'listings' }]" @click="tab = 'listings'">Active</button>
        <button :class="['tab-btn', { active: tab === 'lists' }]" @click="tab = 'lists'">Lists</button>
        <button :class="['tab-btn', { active: tab === 'pipeline' }]" @click="tab = 'pipeline'">Pipeline</button>
        <button :class="['tab-btn', { active: tab === 'duplicates' }]" @click="tab = 'duplicates'">Duplicates</button>
        <button :class="['tab-btn', { active: tab === 'history' }]" @click="tab = 'history'">History</button>
      </nav>
      <div class="tab-content">
        <Listings v-if="tab === 'listings'" :collection-state="collectionState" />
        <History v-else-if="tab === 'history'" />
        <Lists v-else-if="tab === 'lists'" />
        <Pipeline v-else-if="tab === 'pipeline'" />
        <Duplicates v-else />
      </div>
    </div>
  </div>
</template>
