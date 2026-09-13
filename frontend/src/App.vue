<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import Listings from './views/Listings.vue'
import History from './views/History.vue'
import Lists from './views/Lists.vue'

const tab = ref('listings')
</script>

<template>
  <div class="app">
    <Sidebar />
    <div class="main">
      <nav class="tabs">
        <button :class="['tab-btn', { active: tab === 'listings' }]" @click="tab = 'listings'">Active</button>
        <button :class="['tab-btn', { active: tab === 'history' }]" @click="tab = 'history'">History</button>
        <button :class="['tab-btn', { active: tab === 'lists' }]" @click="tab = 'lists'">Lists</button>
      </nav>
      <div class="tab-content">
        <Listings v-if="tab === 'listings'" />
        <History v-else-if="tab === 'history'" />
        <Lists v-else />
      </div>
    </div>
  </div>
</template>
