<script setup>
import { computed, ref } from 'vue'
import ComparisonActions from './ComparisonActions.vue'
import { formatListingAddress } from '../views/listingUtils.js'

const props = defineProps({ listings: { type: Array, default: () => [] }, allLists: { type: Array, default: () => [] } })
const emit = defineEmits(['remove', 'close', 'updated'])
const sortBy = ref('score')
const imageIndexes = ref({})

const rows = [
  ['Price', l => l.price ? `€${Math.round(l.price).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Price / m²', l => l.price && l.surface_area ? `€${Math.round(l.price / l.surface_area).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Score', l => l._score == null ? 'Unknown' : `${Math.round(l._score)} / 100`],
  ['Surface', l => l.surface_area ? `${Math.round(l.surface_area)} m²` : 'Unknown'],
  ['Bedrooms', l => l.bedrooms ?? 'Unknown'],
  ['EPC', l => l.epc_score || 'Unknown'],
  ['Address', l => formatListingAddress(l)],
  ['Postcode', l => l.postcode || 'Unknown'],
  ['Construction year', l => l.construction_year || 'Unknown'],
  ['Terrace', l => (l.outdoor_terrace || l.outdoor_surface) ? 'Yes' : 'Unknown'],
  ['Garden', l => l.outdoor_garden ? 'Yes' : 'Unknown'],
  ['Required cash', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.required_cash).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Estimated loan', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.estimated_loan).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Cash surplus', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.cash_surplus).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Status', l => l._workflow?.status || 'New'],
  ['Follow-up', l => l._workflow?.next_follow_up_date || 'None'],
  ['Portal', l => l.source || 'Unknown'],
]

const sortedListings = computed(() => [...props.listings].sort((a, b) => {
  if (sortBy.value === 'price') return (a.price || Infinity) - (b.price || Infinity)
  if (sortBy.value === 'priceM2') return (a.price && a.surface_area ? a.price / a.surface_area : Infinity) - (b.price && b.surface_area ? b.price / b.surface_area : Infinity)
  if (sortBy.value === 'cash') return (a._purchase_estimate?.required_cash || Infinity) - (b._purchase_estimate?.required_cash || Infinity)
  return (b._score ?? -1) - (a._score ?? -1)
}))

function imageUrls(listing) {
  const detailImages = Object.entries(listing.all_property_details || {})
    .filter(([key, value]) => /^Image \d+ URL$/i.test(key) && value)
    .map(([, value]) => value)
  return [...new Set([listing.image_url_1, listing.image_url_2, ...(Array.isArray(listing.images) ? listing.images : []), ...detailImages].filter(Boolean))]
}

function imageIndex(listing) {
  return imageIndexes.value[listing.url] || 0
}

function changeImage(listing, direction) {
  const images = imageUrls(listing)
  if (images.length < 2) return
  imageIndexes.value[listing.url] = (imageIndex(listing) + direction + images.length) % images.length
}

function rowDiffers(row) {
  const values = sortedListings.value.map(listing => row[1](listing))
  return new Set(values).size > 1
}
</script>

<template>
  <div class="comparison-modal" role="presentation" @click.self="emit('close')">
    <section class="comparison-panel" role="dialog" aria-modal="true" aria-label="Property comparison" tabindex="-1" @keydown.esc="emit('close')">
      <div class="comparison-header">
        <strong>Compare {{ listings.length }} properties</strong>
        <div>
          <label>Sort <select v-model="sortBy"><option value="score">Score</option><option value="price">Price</option><option value="priceM2">Price / m²</option><option value="cash">Required cash</option></select></label>
          <button class="btn btn-ghost btn-sm" type="button" aria-label="Close comparison" @click="emit('close')">Close</button>
        </div>
      </div>
      <div class="comparison-carousels" aria-label="Property images">
        <article v-for="listing in sortedListings" :key="listing.url" class="comparison-carousel">
          <div class="comparison-carousel-image">
            <img v-if="imageUrls(listing).length" :src="imageUrls(listing)[imageIndex(listing)]" :alt="listing.source || listing.postcode || 'Property'" />
            <span v-else>No image available</span>
          </div>
          <div class="comparison-carousel-footer">
            <strong>{{ formatListingAddress(listing) }}</strong>
            <div v-if="imageUrls(listing).length > 1" class="comparison-carousel-controls">
              <button type="button" aria-label="Previous image" @click="changeImage(listing, -1)">‹</button>
              <span>{{ imageIndex(listing) + 1 }} / {{ imageUrls(listing).length }}</span>
              <button type="button" aria-label="Next image" @click="changeImage(listing, 1)">›</button>
            </div>
          </div>
          <ComparisonActions :listing="listing" :all-lists="allLists" @updated="emit('updated')" />
        </article>
      </div>
      <div class="comparison-difference-note"><span class="comparison-difference-swatch"></span>Differences highlighted</div>
      <div class="comparison-scroll"><table><thead><tr><th>Property</th><th v-for="listing in sortedListings" :key="listing.url">{{ listing.postcode || listing.source }} <button class="comparison-remove" type="button" @click="emit('remove', listing.url)" aria-label="Remove property">×</button></th></tr></thead><tbody><tr v-for="row in rows" :key="row[0]"><th>{{ row[0] }}</th><td v-for="listing in sortedListings" :key="listing.url + row[0]" :class="{ 'comparison-difference': rowDiffers(row) }"><a v-if="row[0] === 'Portal' && listing.url" class="comparison-portal-link" :href="listing.url" target="_blank" rel="noopener noreferrer">{{ row[1](listing) }}</a><span v-else>{{ row[1](listing) }}</span></td></tr></tbody></table></div>
    </section>
  </div>
</template>
