<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { formatListingAddress } from './listingUtils.js'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const statuses = ['Interested', 'Contacted', 'Visit planned', 'Offer', 'Rejected']
const listings = ref([])
const loading = ref(false)
const error = ref('')
const saving = ref('')

const columns = computed(() => statuses.map(status => ({
  status,
  listings: listings.value.filter(listing => (listing._workflow?.status || 'New') === status),
})))

const activeCount = computed(() => listings.value.filter(listing => ['Interested', 'Contacted', 'Visit planned', 'Offer'].includes(listing._workflow?.status)).length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    listings.value = await api.listings()
  } catch (cause) {
    error.value = cause.message || 'Could not load the pipeline.'
  }
  loading.value = false
}

async function saveStatus(listing) {
  const key = `${listing.source}:${listing.source_listing_id}`
  saving.value = key
  error.value = ''
  try {
    const workflow = await api.saveWorkflow(listing.source, String(listing.source_listing_id), { ...(listing._workflow || {}), status: listing._workflow?.status || 'New' })
    listing._workflow = { ...listing._workflow, ...workflow }
  } catch (cause) {
    error.value = cause.message || 'Could not save the pipeline status.'
  }
  saving.value = ''
}

function price(listing) {
  return listing.price ? `€${Math.round(listing.price).toLocaleString('nl-BE')}` : 'Price unavailable'
}

function agentMailto(listing) {
  const email = listing.agent_email
  if (!email) return null
  const address = formatListingAddress(listing)
  const price = listing.price ? `€${Math.round(listing.price).toLocaleString('nl-BE')}` : ''
  const subject = `Te koop - ${address}`
  const body = [
    `Goedag,`,
    ``,
    `Ik ben geïnteresseerd in uw eigendom te koop aan ${address}${price ? ` (${price})` : ''}.`,
    listing.url ? `${listing.url}` : '',
    ``,
    `Zou het mogelijk zijn een afspraak te maken voor een bezichtiging?`,
    ``,
    `Met vriendelijke groeten,`,
  ].filter(line => line !== null).join('\n')
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

function image(listing) {
  const details = listing.all_property_details || {}
  const candidates = [
    listing.image_url_1,
    listing.image_url_2,
    details['Image 1 URL'],
    details['Image 2 URL'],
    ...(Array.isArray(listing.images) ? listing.images : []),
  ]
  return candidates.find(value => typeof value === 'string' && value.startsWith('http')) || ''
}

onMounted(load)
</script>

<template>
  <section class="pipeline-view">
    <div class="pipeline-heading">
      <div>
        <p class="pipeline-kicker">Decision workspace</p>
        <h1>Property pipeline</h1>
        <p class="pipeline-summary">{{ activeCount }} active {{ activeCount === 1 ? 'property' : 'properties' }} in progress</p>
      </div>
      <button class="btn btn-secondary" type="button" :disabled="loading" @click="load">{{ loading ? 'Refreshing…' : 'Refresh pipeline' }}</button>
    </div>

    <div v-if="error" class="data-error" role="alert">{{ error }}<button class="btn btn-ghost btn-sm" type="button" @click="load">Retry</button></div>
    <LoadingSpinner v-if="loading && !listings.length" label="Loading pipeline" />
    <div v-else class="pipeline-board" aria-label="Property pipeline board">
      <article v-for="column in columns" :key="column.status" class="pipeline-column">
        <header class="pipeline-column-header">
          <div><h2>{{ column.status }}</h2><span>{{ column.listings.length }}</span></div>
          <div class="pipeline-column-rule" :class="`pipeline-rule-${column.status.toLowerCase().replaceAll(' ', '-')}`"></div>
        </header>
        <div v-if="!column.listings.length" class="pipeline-column-empty">No properties here</div>
        <div v-for="listing in column.listings" :key="listing.url" class="pipeline-card">
          <a v-if="image(listing)" class="pipeline-card-image" :href="listing.url" target="_blank" rel="noopener noreferrer"><img :src="image(listing)" :alt="formatListingAddress(listing)" loading="lazy" /></a>
          <div class="pipeline-card-content">
            <a class="pipeline-card-address" :href="listing.url" target="_blank" rel="noopener noreferrer">{{ formatListingAddress(listing) }}</a>
            <div class="pipeline-card-price">{{ price(listing) }}</div>
            <div class="pipeline-card-meta"><span>{{ listing.source || 'Unknown portal' }}</span><span v-if="listing.bedrooms">{{ listing.bedrooms }} bd</span><span v-if="listing.surface_area">{{ Math.round(listing.surface_area) }} m²</span></div>
            <span v-if="listing.under_option" class="pill pill-yellow">under option</span>
            <div v-if="listing._workflow?.next_follow_up_date" class="pipeline-follow-up">Follow-up {{ listing._workflow.next_follow_up_date }}</div>
            <div v-if="listing.agent_name || listing.agent_phone || listing.agent_email" class="pipeline-agent">
              <span v-if="listing.agent_name" class="pipeline-agent-name">{{ listing.agent_name }}</span>
              <a v-if="listing.agent_phone" class="pipeline-agent-contact" :href="`tel:${listing.agent_phone}`">{{ listing.agent_phone }}</a>
              <a v-if="listing.agent_email" class="pipeline-agent-contact" :href="agentMailto(listing)">{{ listing.agent_email }}</a>
            </div>
            <div class="pipeline-card-controls">
              <select v-model="listing._workflow.status" aria-label="Pipeline status" @change="saveStatus(listing)">
                <option v-for="status in statuses" :key="status">{{ status }}</option>
              </select>
              <span v-if="saving === `${listing.source}:${listing.source_listing_id}`" class="pipeline-saving">Saving…</span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
