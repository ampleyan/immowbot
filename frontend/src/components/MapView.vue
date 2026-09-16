<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const mapHeight = ref(parseInt(localStorage.getItem('map-height') || '480'))
const mapWrap = ref(null)

function startResize(e) {
  e.preventDefault()
  const startY = e.clientY
  const startH = mapHeight.value
  function onMove(ev) {
    const h = Math.max(160, Math.min(700, startH + ev.clientY - startY))
    mapHeight.value = h
    if (map) map.invalidateSize()
  }
  function onUp() {
    localStorage.setItem('map-height', String(mapHeight.value))
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { formatListingAddress } from '../views/listingUtils.js'

const props = defineProps({
  listings: { type: Array, default: () => [] },
})
const emit = defineEmits(['select', 'bounds-change'])

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

function imageUrls(listing) {
  const details = listing.all_property_details || {}
  const seen = new Set()
  const all = [
    listing.image_url_1, listing.image_url_2,
    details['Image 1 URL'], details['Image 2 URL'], details['Image 3 URL'],
    ...(Array.isArray(listing.images) ? listing.images : []),
  ]
  return all.filter(url => typeof url === 'string' && url.startsWith('http') && !seen.has(url) && seen.add(url))
}

function shortDescription(listing) {
  const text = String(listing.description_english || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
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

const LIKED_STATUSES = new Set(['Interested', 'Contacted', 'Visit planned', 'Offer'])

function listingStatus(listing) {
  return listing._workflow?.status || 'New'
}

function listingSignature(listings) {
  return listings.map(listing => [listing.url, listing.latitude, listing.longitude, listing._score, listing.image_url_1, listingStatus(listing), listing._workflow?.rating].join('|')).join(';;')
}

function starsHtml(rating) {
  const n = rating || 0
  return Array.from({ length: 5 }, (_, i) => `<span class="${i < n ? 'mstar filled' : 'mstar'}">${i < n ? '★' : '☆'}</span>`).join('')
}

function cardMarkerHtml(listing) {
  const imgs = imageUrls(listing)
  const color = scoreColor(listing._score)
  const liked = LIKED_STATUSES.has(listingStatus(listing))
  const rating = listing._workflow?.rating || 0
  const price = listing.price ? `€${Math.round(listing.price / 1000)}k` : '—'
  const imgHtml = imgs.length
    ? imgs.map((url, i) => `<img src="${escapeHtml(url)}" referrerpolicy="no-referrer" class="map-card-img${i === 0 ? ' active' : ''}" data-idx="${i}" onerror="this.remove()">`).join('')
    : '<div class="map-card-img active map-card-img-empty"></div>'
  const nav = imgs.length > 1
    ? `<button class="map-carousel-btn map-carousel-prev" data-dir="-1">‹</button><button class="map-carousel-btn map-carousel-next" data-dir="1">›</button><span class="map-carousel-dots">${imgs.map((_, i) => `<i class="map-carousel-dot${i === 0 ? ' active' : ''}"></i>`).join('')}</span>`
    : ''
  return `<div class="map-card-pin" style="--accent:${color}">
    <div class="map-card-img-wrap">
      ${imgHtml}
      <span class="map-card-score" style="background:${color}">${listing._score != null ? Math.round(listing._score) : '—'}</span>
      ${liked ? '<span class="map-card-liked">♥</span>' : ''}
      ${nav}
    </div>
    <div class="map-card-footer">
      <span class="map-card-price">${price}</span>
      <span class="map-card-stars">${rating ? starsHtml(rating) : ''}</span>
    </div>
    <div class="map-card-arrow" style="border-top-color:${color}"></div>
  </div>`
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
    const W = 160, H = 110
    const marker = L.marker(latLng, {
      icon: L.divIcon({
        className: 'map-card-marker',
        html: cardMarkerHtml(listing),
        iconSize: [W, H],
        iconAnchor: [W / 2, H],
      }),
      title: listing.postcode || listing.property_type || 'Property',
    })
    marker.bindPopup(popupHtml(listing), { closeButton: true, maxWidth: 380, minWidth: 320 })
    marker.on('popupopen', event => {
      const button = event.popup.getElement()?.querySelector('[data-listing-url]')
      button?.addEventListener('click', () => emit('select', listing.url))
    })
    marker.on('add', () => {
      const el = marker.getElement()
      if (!el) return
      L.DomEvent.disableScrollPropagation(el)
      const imgs = el.querySelectorAll('.map-card-img[data-idx]')
      const dots = el.querySelectorAll('.map-carousel-dot')
      if (imgs.length < 2) return
      let current = 0
      el.querySelectorAll('.map-carousel-btn').forEach(btn => {
        L.DomEvent.disableClickPropagation(btn)
        btn.addEventListener('click', () => {
          imgs[current].classList.remove('active')
          dots[current]?.classList.remove('active')
          current = (current + Number(btn.dataset.dir) + imgs.length) % imgs.length
          imgs[current].classList.add('active')
          dots[current]?.classList.add('active')
        })
      })
    })
    marker.addTo(markerLayer)
  }
  if (!viewportInitialized && bounds.length === 1) map.setView(bounds[0], 13)
  if (!viewportInitialized && bounds.length > 1) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 })
  if (bounds.length) viewportInitialized = true
}

function emitBounds() {
  if (!map) return
  const b = map.getBounds()
  emit('bounds-change', { north: b.getNorth(), south: b.getSouth(), east: b.getEast(), west: b.getWest() })
}

onMounted(() => {
  map = L.map(mapElement.value, { zoomControl: true })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)
  markerLayer = L.layerGroup().addTo(map)
  map.setView([50.85, 4.35], 8)
  map.on('moveend zoomend', emitBounds)
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
  <div ref="mapWrap" class="map-wrap">
    <div ref="mapElement" class="listing-map" :style="{ height: mapHeight + 'px' }" aria-label="Property map"></div>
    <div class="map-legend" aria-label="Map marker legend">
      <span><i class="legend-dot strong"></i> Strong match</span>
      <span><i class="legend-dot look"></i> Worth a look</span>
      <span><i class="legend-dot review"></i> Review</span>
      <span><i class="legend-dot excluded"></i> Excluded</span>
    </div>
    <div class="map-resize-handle" @mousedown="startResize" title="Drag to resize map"></div>
  </div>
</template>
