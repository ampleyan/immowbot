<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api.js'
import Login from './components/Login.vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import History from './views/History.vue'
import Lists from './views/Lists.vue'
import Pipeline from './views/Pipeline.vue'

const tab = ref('listings')
const authenticated = ref(false)
const checkingAuth = ref(true)

onMounted(async () => {
  try {
    await api.me()
    authenticated.value = true
  } catch {}
  checkingAuth.value = false
})
</script>

<template>
  <Login v-if="!checkingAuth && !authenticated" @authenticated="authenticated = true" />
  <div v-else-if="authenticated" class="app">
    <Sidebar />
    <div class="main">
      <nav class="tabs">
        <button :class="['tab-btn', { active: tab === 'listings' }]" @click="tab = 'listings'">Active</button>
        <button :class="['tab-btn', { active: tab === 'history' }]" @click="tab = 'history'">History</button>
        <button :class="['tab-btn', { active: tab === 'lists' }]" @click="tab = 'lists'">Lists</button>
        <button :class="['tab-btn', { active: tab === 'pipeline' }]" @click="tab = 'pipeline'">Pipeline</button>
      </nav>
      <div class="tab-content">
        <Listings v-if="tab === 'listings'" />
        <History v-else-if="tab === 'history'" />
        <Lists v-else-if="tab === 'lists'" />
        <Pipeline v-else />
      </div>
    </div>
  </div>
</template>
