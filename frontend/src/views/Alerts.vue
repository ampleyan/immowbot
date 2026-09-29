<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import DetailPanel from '../components/DetailPanel.vue'

const emit = defineEmits(['alerts-cleared'])

const listings = ref([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const selectedUrl = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const alerts = await api.getAlerts()
    const unread = alerts.filter(a => !a.read_at)
    if (!unread.length) { listings.value = []; return }
    const ids = unread.map(a => ({ source: a.source, source_listing_id: a.source_listing_id }))
    listings.value = await api.getListingsBatch(ids)
  } catch (e) {
    error.value = e.message
    listings.value = []
  } finally {
    loading.value = false
  }
}

function toggleDetail(url) {
  selectedUrl.value = selectedUrl.value === url ? null : url
}

async function clearAll() {
  actionError.value = ''
  try {
    await api.clearAlerts()
    listings.value = []
    selectedUrl.value = null
    emit('alerts-cleared')
  } catch (cause) {
    actionError.value = cause.message || 'Could not clear alerts. Try again.'
  }
}

onMounted(load)
</script>

<template>
  <div class="alerts-view">
    <div class="alerts-view-header">
      <h2 class="alerts-view-title">New matches <span v-if="listings.length" class="alerts-view-count">{{ listings.length }}</span></h2>
      <button class="btn btn-secondary btn-sm" :disabled="loading || !listings.length" @click="clearAll">Clear all</button>
    </div>
    <div v-if="actionError" class="data-error" role="alert">{{ actionError }}</div>
    <div v-if="loading" class="alerts-view-empty">Loading…</div>
    <div v-else-if="error" class="alerts-view-empty" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="btn btn-secondary btn-sm" @click="load">Try again</button>
    </div>
    <div v-else-if="!listings.length" class="alerts-view-empty">No new alerts. New matches will appear here after a collection.</div>
    <div v-else class="cards-grid">
      <template v-for="listing in listings" :key="listing.source + ':' + listing.source_listing_id">
        <PropertyCard
          :listing="listing"
          :showSelect="false"
          @toggle-detail="toggleDetail(listing.url)"
        />
        <DetailPanel
          v-if="selectedUrl === listing.url"
          :listing="listing"
          @updated="load"
        />
      </template>
    </div>
  </div>
</template>
