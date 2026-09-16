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

const props = defineProps<{ group: DuplicateGroupData; modelValue: string }>()
const emit = defineEmits<{ changed: []; 'update:modelValue': [key: string] }>()
const apiClient = api as {
  deleteListing: (source: string, sourceListingId: string) => Promise<unknown>
}

const busy = ref(false)

function offerKey(offer: Offer) {
  return `${offer.source}:${offer.source_listing_id}`
}

function toggleSelection(offer: Offer) {
  const key = offerKey(offer)
  emit('update:modelValue', props.modelValue === key ? '' : key)
}

function openListing(offer: Offer) {
  if (offer.url) window.open(offer.url, '_blank', 'noopener')
}

function groupExplanations() {
  const canonical = props.group.canonical
  return props.group.offers.slice(1).map((offer, index) => {
    const reasons = props.group.signals[index]?.signals.join(', ') || 'the available duplicate signals'
    return `${offer.source} #${offer.source_listing_id} — Potential duplicate of ${canonical.source} #${canonical.source_listing_id} because of ${reasons}.`
  })
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
</script>

<template>
  <section class="duplicate-group">
    <div class="duplicate-group-header">
      <div><strong>{{ group.confidence }} confidence</strong> · {{ group.offers.length }} possible offers</div>
      <small>Compared across {{ group.signals.map(s => s.source).filter((source, index, sources) => sources.indexOf(source) === index).join(', ') }}</small>
    </div>
    <div class="duplicate-match-reason" aria-label="Why these listings are grouped">
      <strong>Why grouped</strong>
      <p v-for="reason in groupExplanations()" :key="reason">{{ reason }}</p>
    </div>
    <p class="duplicate-instruction">Select one offer to keep, or delete offers you confirm are not duplicates.</p>
    <div :class="['duplicate-offers-grid', group.offers.length === 2 ? 'duplicate-offers-grid--two' : '']">
      <div v-for="offer in group.offers" :key="offerKey(offer)" class="duplicate-offer-card">
        <label class="duplicate-keep-option">
          <input type="checkbox" :checked="modelValue === offerKey(offer)" :aria-label="'Select ' + offer.source + ' listing to keep'" @change="toggleSelection(offer)" />
        </label>
        <PropertyCard :listing="{ ...offer, _score: offer._score ?? null }" :showSelect="false" @toggle-detail="openListing(offer)" />
        <button type="button" class="btn btn-ghost btn-sm duplicate-delete" :disabled="busy" @click="deleteOffer(offer)">Delete</button>
      </div>
    </div>
  </section>
</template>
