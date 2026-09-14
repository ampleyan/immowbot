<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api.js'
import PropertyCard from './PropertyCard.vue'

type Offer = {
  source: string
  source_listing_id: string | number
  url?: string
  [key: string]: unknown
}

type Signal = { source: string; signals: string[] }
type DuplicateGroupData = { canonical: Offer; offers: Offer[]; confidence: string; signals: Signal[] }

const props = defineProps<{ group: DuplicateGroupData }>()
const emit = defineEmits<{ changed: [] }>()
const apiClient = api as {
  deleteListing: (source: string, sourceListingId: string) => Promise<unknown>
  mergeDuplicates: (keep: { source: string; source_listing_id: string }, remove: Array<{ source: string; source_listing_id: string }>) => Promise<unknown>
}

const selectedKey = ref('')
const busy = ref(false)

function offerKey(offer: Offer) {
  return `${offer.source}:${offer.source_listing_id}`
}

function selectedOffer(): Offer {
  const first = props.group.offers[0]
  if (!first) throw new Error('Duplicate group has no offers')
  return props.group.offers.find(offer => offerKey(offer) === selectedKey.value) || first
}

function toggleSelection(offer: Offer) {
  const key = offerKey(offer)
  selectedKey.value = selectedKey.value === key ? '' : key
}

function openListing(offer: Offer) {
  if (offer.url) window.open(offer.url, '_blank', 'noopener')
}

function explanation(offer: Offer, index: number) {
  if (index === 0) return `Reference offer matched by ${props.group.signals.map(signal => signal.signals.join(' and ')).join('; ') || 'the available duplicate signals'}.`
  const signal = props.group.signals[index - 1]
  const reasons = signal?.signals.join(', ') || 'the available duplicate signals'
  const canonical = props.group.canonical
  return `Potential duplicate of ${canonical.source} #${canonical.source_listing_id} because of ${reasons}.`
}

const signalLabels: Record<string, string> = {
  address: 'Same address',
  postcode: 'Same postcode',
  coordinates: 'Nearby coordinates',
  price: 'Same price',
  surface: 'Similar surface',
  bedrooms: 'Same bedrooms',
}

function groupReasons() {
  return [...new Set(props.group.signals.flatMap(signal => signal.signals))].map(signal => signalLabels[signal] || signal)
}

async function deleteOffer(offer: Offer) {
  if (!window.confirm(`Delete the ${offer.source} offer?`)) return
  busy.value = true
  try {
    await apiClient.deleteListing(offer.source, String(offer.source_listing_id))
    emit('changed')
  } finally {
    busy.value = false
  }
}

async function mergeGroup() {
  const keep = selectedOffer()
  const remove = props.group.offers.filter(offer => offerKey(offer) !== offerKey(keep)).map(offer => ({
    source: offer.source,
    source_listing_id: String(offer.source_listing_id),
  }))
  if (!remove.length || !window.confirm(`Keep the ${keep.source} listing and remove ${remove.length} duplicate offer${remove.length === 1 ? '' : 's'}?`)) return
  busy.value = true
  try {
    await apiClient.mergeDuplicates({ source: keep.source, source_listing_id: String(keep.source_listing_id) }, remove)
    emit('changed')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="duplicate-group">
    <div class="duplicate-group-header">
      <div><strong>{{ group.confidence }} confidence</strong> · {{ group.offers.length }} possible offers</div>
      <small>Compared across {{ group.signals.map(s => s.source).filter((source, index, sources) => sources.indexOf(source) === index).join(', ') }}</small>
    </div>
    <div class="duplicate-match-reason" aria-label="Why these listings are grouped">
      <strong>Why grouped</strong>
      <span v-for="reason in groupReasons()" :key="reason" class="duplicate-reason-chip">{{ reason }}</span>
    </div>
    <p class="duplicate-instruction">Select one offer to keep, or delete offers you confirm are not duplicates.</p>
    <div v-for="(offer, index) in group.offers" :key="offerKey(offer)" class="duplicate-offer-card">
      <p class="duplicate-explanation"><strong>{{ offer.source }} #{{ offer.source_listing_id }}</strong> — {{ explanation(offer, index) }}</p>
      <label class="duplicate-keep-option">
        <input type="checkbox" :checked="selectedKey === offerKey(offer)" :aria-label="'Select ' + offer.source + ' listing to keep'" @change="toggleSelection(offer)" />
      </label>
      <PropertyCard :listing="{ ...offer, _score: offer._score ?? null }" @toggle-detail="openListing(offer)" />
      <button type="button" class="btn btn-ghost btn-sm duplicate-delete" :disabled="busy" @click="deleteOffer(offer)">Delete this offer</button>
    </div>
    <button v-if="selectedKey" type="button" class="btn btn-primary btn-sm merge-duplicates" :disabled="busy" @click="mergeGroup">{{ busy ? 'Updating…' : 'Merge selected with duplicates' }}</button>
  </section>
</template>
