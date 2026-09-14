<script setup>
import { computed, ref } from 'vue'

const props = defineProps({ listings: { type: Array, default: () => [] } })
const emit = defineEmits(['remove', 'close'])
const sortBy = ref('score')

const rows = [
  ['Price', l => l.price ? `€${Math.round(l.price).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Price / m²', l => l.price && l.surface_area ? `€${Math.round(l.price / l.surface_area).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Score', l => l._score == null ? 'Unknown' : `${Math.round(l._score)} / 100`],
  ['Surface', l => l.surface_area ? `${Math.round(l.surface_area)} m²` : 'Unknown'],
  ['Bedrooms', l => l.bedrooms ?? 'Unknown'],
  ['EPC', l => l.epc_score || 'Unknown'],
  ['Postcode', l => l.postcode || 'Unknown'],
  ['Construction year', l => l.construction_year || 'Unknown'],
  ['Terrace', l => (l.outdoor_terrace || l.outdoor_surface) ? 'Yes' : 'Unknown'],
  ['Garden', l => l.outdoor_garden ? 'Yes' : 'Unknown'],
  ['Required cash', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.required_cash).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Estimated loan', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.estimated_loan).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Cash surplus', l => l._purchase_estimate?.available ? `€${Math.round(l._purchase_estimate.cash_surplus).toLocaleString('nl-BE')}` : 'Unknown'],
  ['Status', l => l._workflow?.status || 'New'],
  ['Follow-up', l => l._workflow?.next_follow_up_date || 'None'],
  ['Commute', l => l._commute?.available && l._commute.destinations?.length ? `${Math.round(l._commute.destinations.reduce((total, destination) => total + destination.minutes, 0) / l._commute.destinations.length)} min avg` : 'Unknown'],
  ['Portal', l => l.source || 'Unknown'],
]

const sortedListings = computed(() => [...props.listings].sort((a, b) => {
  if (sortBy.value === 'price') return (a.price || Infinity) - (b.price || Infinity)
  if (sortBy.value === 'priceM2') return (a.price && a.surface_area ? a.price / a.surface_area : Infinity) - (b.price && b.surface_area ? b.price / b.surface_area : Infinity)
  if (sortBy.value === 'cash') return (a._purchase_estimate?.required_cash || Infinity) - (b._purchase_estimate?.required_cash || Infinity)
  return (b._score ?? -1) - (a._score ?? -1)
}))
</script>

<template>
  <section class="comparison-panel" aria-label="Property comparison">
    <div class="comparison-header"><strong>Compare {{ listings.length }} properties</strong><div><label>Sort <select v-model="sortBy"><option value="score">Score</option><option value="price">Price</option><option value="priceM2">Price / m²</option><option value="cash">Required cash</option></select></label><button class="btn btn-ghost btn-sm" @click="emit('close')">Close</button></div></div>
    <div class="comparison-scroll"><table><thead><tr><th>Property</th><th v-for="listing in sortedListings" :key="listing.url">{{ listing.postcode || listing.source }} <button class="comparison-remove" @click="emit('remove', listing.url)" aria-label="Remove property">×</button></th></tr></thead><tbody><tr v-for="[label, formatter] in rows" :key="label"><th>{{ label }}</th><td v-for="listing in sortedListings" :key="listing.url + label">{{ formatter(listing) }}</td></tr></tbody></table></div>
  </section>
</template>
