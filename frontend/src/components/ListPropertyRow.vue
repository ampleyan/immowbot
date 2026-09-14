<script setup lang="ts">
import { formatListingAddress } from '../views/listingUtils.js'

defineProps({
  listing: { type: Object, required: true },
  removable: { type: Boolean, default: false },
})

const emit = defineEmits(['open', 'remove'])

function fmtPrice(price: number | null | undefined) {
  if (!price) return '—'
  return '€' + Math.round(price).toLocaleString('nl-BE')
}

function specs(listing: Record<string, unknown>) {
  const parts = []
  if (listing.bedrooms) parts.push(`${Math.round(Number(listing.bedrooms))} bd`)
  if (listing.surface_area) parts.push(`${Math.round(Number(listing.surface_area))} m²`)
  if (listing.postcode) parts.push(String(listing.postcode))
  return parts.join(' · ') || '—'
}

function imageUrl(listing: Record<string, unknown>) {
  if (typeof listing.image_url_1 === 'string') return listing.image_url_1
  if (Array.isArray(listing.images) && typeof listing.images[0] === 'string') return listing.images[0]
  if (typeof listing.image_url === 'string') return listing.image_url
  return ''
}
</script>

<template>
  <article class="list-property">
    <div class="list-property-media">
      <img v-if="imageUrl(listing)" :src="imageUrl(listing)" :alt="listing.source || 'Property'" loading="lazy" />
      <div v-else class="list-property-placeholder">🏠</div>
    </div>
    <div class="list-property-data">
      <div class="list-property-price-row">
        <strong class="list-property-price">{{ fmtPrice(listing.price) }}</strong>
        <span class="list-property-type">{{ (listing.property_type || 'Property').replace(/^\w/, (c: string) => c.toUpperCase()) }}</span>
      </div>
      <div class="list-property-specs">{{ specs(listing) }}</div>
      <div class="list-property-address">{{ formatListingAddress(listing) }}</div>
      <div class="list-property-badges">
        <span v-if="listing.epc_score" class="pill-epc">EPC {{ listing.epc_score }}</span>
        <span class="pill pill-neutral">{{ listing.source }}</span>
        <span v-if="listing._score !== null && listing._score !== undefined" class="pill pill-blue">Score {{ Math.round(listing._score) }}</span>
      </div>
    </div>
    <div class="list-property-actions">
      <button class="btn btn-secondary btn-sm" @click="emit('open')">Open</button>
      <button v-if="removable" class="btn btn-ghost btn-sm grouped-remove" @click="emit('remove')">Remove</button>
    </div>
  </article>
</template>
