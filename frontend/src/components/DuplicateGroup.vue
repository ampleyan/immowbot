<script setup>
import { ref } from 'vue'
import { api } from '../api.js'
import PropertyCard from './PropertyCard.vue'

const props = defineProps({
  group: { type: Object, required: true },
})
const emit = defineEmits(['changed'])

const selectedKey = ref(offerKey(props.group.canonical))
const busy = ref(false)

function offerKey(offer) {
  return `${offer.source}:${offer.source_listing_id}`
}

function selectedOffer() {
  return props.group.offers.find(offer => offerKey(offer) === selectedKey.value) || props.group.offers[0]
}

function openListing(offer) {
  if (offer.url) window.open(offer.url, '_blank', 'noopener')
}

async function deleteOffer(offer) {
  if (!window.confirm(`Delete the ${offer.source} offer?`)) return
  busy.value = true
  try {
    await api.deleteListing(offer.source, String(offer.source_listing_id))
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
    await api.mergeDuplicates({ source: keep.source, source_listing_id: String(keep.source_listing_id) }, remove)
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
      <small>Signals: {{ group.signals.map(s => s.source + ' (' + s.signals.join(', ') + ')').join('; ') }}</small>
    </div>
    <p class="duplicate-instruction">Choose the listing to keep, or delete offers you confirm are not duplicates.</p>
    <div v-for="offer in group.offers" :key="offerKey(offer)" class="duplicate-offer-card">
      <label class="duplicate-keep-option">
        <input v-model="selectedKey" type="radio" :name="'duplicate-keep-' + group.canonical.url" :value="offerKey(offer)" />
        Keep this listing
      </label>
      <PropertyCard :listing="{ ...offer, _score: offer._score ?? null }" @toggle-detail="openListing(offer)" />
      <button type="button" class="btn btn-ghost btn-sm duplicate-delete" :disabled="busy" @click="deleteOffer(offer)">Delete this offer</button>
    </div>
    <button type="button" class="btn btn-primary btn-sm merge-duplicates" :disabled="busy" @click="mergeGroup">{{ busy ? 'Updating…' : 'Merge duplicates' }}</button>
  </section>
</template>
