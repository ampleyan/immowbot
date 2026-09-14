<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { formatListingAddress } from '../views/listingUtils.js'

const props = defineProps({
  listings: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const mapElement = ref(null)
let map = null
let markerLayer = null
let viewportInitialized = false
let lastSignature = ''

function scoreColor(score) {
  if (score === null || score === undefined) return '#667085'
  if (score >= 75) return '#027A48'
  if (score >= 55) return '#B54708'
  return '#C01048'
}

function qualityLabel(listing) {
  if (listing._score === null || listing._score === undefined) return 'Excluded'
  if (listing._score >= 75) return 'Strong match'
  if (listing._score >= 55) return 'Worth a look'
  return 'Review carefully'
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char])
}

function mappableListings() {
  return props.listings.filter(listing => listing.latitude !== null && listing.latitude !== undefined && listing.latitude !== '' && listing.longitude !== null && listing.longitude !== undefined && listing.longitude !== '' && Number.isFinite(Number(listing.latitude)) && Number.isFinite(Number(listing.longitude)))
}

function imageUrl(listing) {
  const details = listing.all_property_details || {}
  const candidates = [
    listing.image_url_1,
    listing.image_url_2,
    details['Image 1 URL'],
    details['Image 2 URL'],
    ...(Array.isArray(listing.images) ? listing.images : []),
  ]
  return candidates.find(url => typeof url === 'string' && url.startsWith('http')) || null
}

function shortDescription(listing) {
  const text = String(listing.description_english || listing.description || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
  return text.length > 180 ? `${text.slice(0, 180).trimEnd()}…` : text
}

function popupHtml(listing) {
  const image = imageUrl(listing)
  const imageMarkup = image ? `<img src="${escapeHtml(image)}" alt="Property photo" referrerpolicy="no-referrer" class="map-popup-image">` : '<div class="map-popup-image map-popup-image-empty">No photo available</div>'
  const score = listing._score === null || listing._score === undefined ? 'Excluded' : `Score ${Math.round(listing._score)} / 100`
  const facts = [
    listing.surface_area ? `${escapeHtml(listing.surface_area)} m²` : '',
    listing.bedrooms ? `${escapeHtml(listing.bedrooms)} beds` : '',
    listing.epc_score ? `EPC ${escapeHtml(listing.epc_score)}` : '',
  ].filter(Boolean).join(' · ')
  const description = shortDescription(listing)
  return `<div class="map-popup"><div class="map-popup-accent" style="background:${scoreColor(listing._score)}"></div>${imageMarkup}<div class="map-popup-body"><div class="map-popup-title">${escapeHtml(formatListingAddress(listing))}</div><div class="map-popup-subtitle">${escapeHtml(listing.property_type || 'Property')}</div><div class="map-popup-price">€${Math.round(listing.price || 0).toLocaleString('nl-BE')}</div><div class="map-popup-score" style="color:${scoreColor(listing._score)}">${escapeHtml(qualityLabel(listing))} · ${escapeHtml(score)}</div>${facts ? `<div class="map-popup-facts">${facts}</div>` : ''}${description ? `<div class="map-popup-description">${escapeHtml(description)}</div>` : ''}<button type="button" data-listing-url="${escapeHtml(listing.url)}">View full details</button></div></div>`
}

function listingSignature(listings) {
  return listings.map(listing => [listing.url, listing.latitude, listing.longitude, listing._score, listing.image_url_1].join('|')).join(';;')
}

function renderMarkers() {
  if (!map || !markerLayer) return
  const markers = mappableListings()
  const signature = listingSignature(markers)
  if (signature === lastSignature) return
  lastSignature = signature
  markerLayer.clearLayers()
  const bounds = []
  for (const listing of markers) {
    const latLng = [Number(listing.latitude), Number(listing.longitude)]
    bounds.push(latLng)
    const marker = L.marker(latLng, {
      icon: L.divIcon({
        className: 'score-marker',
        html: `<span style="background:${scoreColor(listing._score)}">${listing._score === null || listing._score === undefined ? '—' : Math.round(listing._score)}</span>`,
        iconSize: [38, 26],
        iconAnchor: [19, 13],
      }),
      title: listing.postcode || listing.property_type || 'Property',
    })
    marker.bindPopup(popupHtml(listing), { closeButton: true, maxWidth: 380, minWidth: 320 })
    marker.on('popupopen', event => {
      const button = event.popup.getElement()?.querySelector('[data-listing-url]')
      button?.addEventListener('click', () => emit('select', listing.url))
    })
    marker.addTo(markerLayer)
  }
  if (!viewportInitialized && bounds.length === 1) map.setView(bounds[0], 13)
  if (!viewportInitialized && bounds.length > 1) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 })
  if (bounds.length) viewportInitialized = true
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
  viewportInitialized = false
  lastSignature = ''
})
</script>

<template>
  <div class="map-wrap">
    <div ref="mapElement" class="listing-map" aria-label="Property map"></div>
    <div class="map-legend" aria-label="Map marker legend">
      <span><i class="legend-dot strong"></i> Strong match</span>
      <span><i class="legend-dot look"></i> Worth a look</span>
      <span><i class="legend-dot review"></i> Review</span>
      <span><i class="legend-dot excluded"></i> Excluded</span>
    </div>
  </div>
</template>
