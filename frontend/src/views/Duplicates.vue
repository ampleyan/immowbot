<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import DuplicateGroup from '../components/DuplicateGroup.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const duplicates = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    duplicates.value = await api.getDuplicates()
  } catch (cause) {
    error.value = cause.message || 'Could not load possible duplicates.'
  }
  loading.value = false
}

onMounted(load)
</script>

<template>
  <section class="duplicates-view">
    <div class="duplicates-heading">
      <div><p class="pipeline-kicker">Review workspace</p><h1>Possible duplicates</h1><p>Listings are grouped only when their address, postcode, price, and surface match.</p></div>
      <button class="btn btn-secondary" type="button" :disabled="loading" @click="load">{{ loading ? 'Refreshing…' : 'Refresh' }}</button>
    </div>
    <div v-if="error" class="data-error" role="alert">{{ error }}<button class="btn btn-ghost btn-sm" type="button" @click="load">Retry</button></div>
    <LoadingSpinner v-if="loading && !duplicates.length" label="Checking duplicates" />
    <div v-else-if="!duplicates.length" class="empty">No possible duplicates found.</div>
    <DuplicateGroup v-for="group in duplicates" v-else :key="group.canonical.url" :group="group" @changed="load" />
  </section>
</template>
