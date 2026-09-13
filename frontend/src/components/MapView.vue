<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  listings: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const mapElement = ref(null)
let map = null
let markerLayer = null

function scoreColor(score) {
  if (score === null || score === undefined) return '#667085'
  if (score >= 75) return '#027A48'
  if (score >= 55) return '#B54708'
  return '#C01048'
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char])
}

function mappableListings() {
  return props.listings.filter(listing => listing.latitude !== null && listing.latitude !== undefined && listing.latitude !== '' && listing.longitude !== null && listing.longitude !== undefined && listing.longitude !== '' && Number.isFinite(Number(listing.latitude)) && Number.isFinite(Number(listing.longitude)))
}

function popupHtml(listing) {
  const score = listing._score === null || listing._score === undefined ? 'Excluded' : `Score ${Math.round(listing._score)}`
  return `<div class="map-popup"><strong>${escapeHtml(listing.postcode || 'Location unavailable')}</strong><br>${escapeHtml(listing.property_type || 'Property')} · €${Math.round(listing.price || 0).toLocaleString('nl-BE')}<br><span>${escapeHtml(score)}</span><button type="button" data-listing-url="${escapeHtml(listing.url)}">View details</button></div>`
}

function renderMarkers() {
  if (!map || !markerLayer) return
  markerLayer.clearLayers()
  const markers = mappableListings()
  const bounds = []
  for (const listing of markers) {
    const latLng = [Number(listing.latitude), Number(listing.longitude)]
    bounds.push(latLng)
    const marker = L.marker(latLng, {
      icon: L.divIcon({
        className: 'score-marker',
        html: `<span style="background:${scoreColor(listing._score)}"></span>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      }),
      title: listing.postcode || listing.property_type || 'Property',
    })
    marker.bindPopup(popupHtml(listing), { closeButton: true, maxWidth: 220 })
    marker.on('popupopen', event => {
      const button = event.popup.getElement()?.querySelector('[data-listing-url]')
      button?.addEventListener('click', () => emit('select', listing.url))
    })
    marker.addTo(markerLayer)
  }
  if (bounds.length === 1) map.setView(bounds[0], 13)
  if (bounds.length > 1) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 })
}

onMounted(() => {
  map = L.map(mapElement.value, { zoomControl: true })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)
  markerLayer = L.layerGroup().addTo(map)
  map.setView([50.85, 4.35], 8)
  renderMarkers()
})

watch(() => props.listings, renderMarkers, { deep: true })

onBeforeUnmount(() => {
  map?.remove()
  map = null
  markerLayer = null
})
</script>

<template>
  <div ref="mapElement" class="listing-map" aria-label="Property map"></div>
</template>
