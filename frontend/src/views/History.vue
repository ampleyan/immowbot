<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const runs = ref([])
const expanded = ref(new Set())
const runListings = ref({})
const loading = ref(true)
const error = ref('')
const runErrors = ref({})

async function load() {
  loading.value = true
  error.value = ''
  try {
    runs.value = await api.getRuns()
  } catch (cause) {
    error.value = cause.message || 'Could not load collection history.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function loadRunListings(runId) {
  runErrors.value = { ...runErrors.value, [runId]: '' }
  try {
    runListings.value[runId] = await api.getRunListings(runId)
  } catch (cause) {
    runErrors.value = { ...runErrors.value, [runId]: cause.message || 'Could not load listings for this run.' }
  }
}

async function toggle(runId) {
  const s = new Set(expanded.value)
  if (s.has(runId)) {
    s.delete(runId)
  } else {
    s.add(runId)
    if (!runListings.value[runId]) {
      await loadRunListings(runId)
    }
  }
  expanded.value = s
}

function fmtTime(iso) {
  if (!iso) return '?'
  return iso.slice(0, 19).replace('T', ' ')
}

function fmtPrice(p) {
  if (!p) return '—'
  return '€' + Math.round(p).toLocaleString('nl-BE')
}

const STATUS = {
  ok: { color: '#039855', dot: '#039855', label: 'OK' },
  partial: { color: '#D97706', dot: '#D97706', label: 'Partial' },
  cancelled: { color: '#667085', dot: '#667085', label: 'Cancelled' },
  running: { color: '#2563EB', dot: '#2563EB', label: 'Running' },
}

function statusInfo(s) {
  return STATUS[s] || { color: '#344054', dot: '#98A2B3', label: s || '?' }
}
</script>

<template>
  <div>
    <LoadingSpinner v-if="loading" label="Loading history" />
    <div v-else-if="error" class="data-error" role="alert">
      <span>{{ error }}</span>
      <button type="button" class="btn btn-secondary btn-sm" @click="load">Try again</button>
    </div>
    <div v-else-if="!runs.length" class="empty">No runs yet.</div>

    <div v-for="run in runs" :key="run.id" class="run-item">
      <button class="run-header" type="button" :aria-expanded="expanded.has(run.id)" :aria-controls="`run-body-${run.id}`" @click="toggle(run.id)">
        <div class="run-status-dot" :style="{ background: statusInfo(run.status).dot }"></div>
        <span class="run-id">Run #{{ run.id }}</span>
        <span class="run-time">{{ fmtTime(run.started_at) }}</span>
        <span class="run-status-text" :style="{ color: statusInfo(run.status).color }">{{ statusInfo(run.status).label }}</span>
        <span :class="['run-chevron', { open: expanded.has(run.id) }]">▼</span>
      </button>

      <div v-if="expanded.has(run.id)" :id="`run-body-${run.id}`" class="run-body">
        <div class="run-sources">
          <div v-for="s in run.sources" :key="s.source" class="run-source-item">
            <div class="source-dot" :style="{ background: s.status === 'ok' ? '#039855' : '#DC2626' }"></div>
            <strong>{{ s.source }}</strong>&nbsp;— {{ s.count }} saved
          </div>
        </div>

        <div v-if="runErrors[run.id]" class="data-error" role="alert">
          <span>{{ runErrors[run.id] }}</span>
          <button type="button" class="btn btn-secondary btn-sm" @click="loadRunListings(run.id)">Try again</button>
        </div>
        <div v-else-if="!runListings[run.id]" style="font-size:0.8rem;color:#667085">Loading…</div>
        <div v-else-if="!runListings[run.id].length" class="empty" style="padding:0.5rem 0">Nothing saved in this run.</div>
        <table v-else class="run-table">
          <thead>
            <tr>
              <th>Name / URL</th>
              <th>Price</th>
              <th>Type</th>
              <th>Post</th>
              <th>m²</th>
              <th>Beds</th>
              <th>EPC</th>
              <th>Portal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in runListings[run.id]" :key="l.url">
              <td>
                <a :href="l.url" target="_blank">
                  {{ ((l.name || l.address || l.street || l.url || '').slice(0, 40) + (((l.name || l.url || '').length > 40) ? '…' : '')) }}
                </a>
              </td>
              <td>{{ fmtPrice(l.price) }}</td>
              <td>{{ (l.property_type || '').replace(/^\w/, c => c.toUpperCase()) }}</td>
              <td>{{ l.postcode || '—' }}</td>
              <td>{{ l.surface_area || '?' }}</td>
              <td>{{ l.bedrooms || '?' }}</td>
              <td>{{ l.epc_score || '—' }}</td>
              <td>{{ l.source || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
