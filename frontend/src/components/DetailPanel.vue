<script setup>
import { ref, computed } from 'vue'

const props = defineProps(['listing'])

const EPC_COLORS = {
  'A++': '#006B3C', 'A+': '#006B3C', 'A': '#006B3C',
  'B': '#2D8A4E', 'C': '#7AB648',
  'D': '#F5C400', 'E': '#F0A500',
  'F': '#D93E1F', 'G': '#9B1B0E',
}

const SCORE_COMPONENTS = [
  { key: 'price', label: 'Price headroom', max: 30 },
  { key: 'surface_area', label: 'Surface', max: 25 },
  { key: 'bedrooms', label: 'Bedrooms', max: 15 },
  { key: 'epc', label: 'EPC', max: 20 },
  { key: 'completeness', label: 'Completeness', max: 10 },
]

const imageIdx = ref(0)
const modalOpen = ref(false)

const images = computed(() => {
  const l = props.listing
  const d = l.all_property_details || {}
  const candidates = [
    l.image_url_1, l.image_url_2,
    d['Image 1 URL'], d['Image 2 URL'],
    ...(Array.isArray(l.images) ? l.images : []),
  ]
  return candidates.filter(u => typeof u === 'string' && u.startsWith('http'))
})

function fmtPrice(p) {
  if (!p) return '—'
  return '€' + Math.round(p).toLocaleString('nl-BE')
}

function scoreColor(score) {
  if (!score) return '#98A2B3'
  if (score >= 60) return '#027A48'
  if (score >= 40) return '#B54708'
  return '#C01048'
}

function typeLabel(type) {
  return (type || 'Property').replace(/^\w/, c => c.toUpperCase())
}

function descriptionText(listing) {
  const raw = listing.description_english || listing.description || ''
  const readable = String(raw)
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return readable.length > 1200 ? `${readable.slice(0, 1200).trimEnd()}…` : readable
}

const details = computed(() => {
  const l = props.listing
  return [
    ['Postcode', l.postcode],
    ['Type', (l.property_type || '').replace(/^\w/, c => c.toUpperCase())],
    ['Portal', l.source],
    ['Built', l.construction_year],
    ['Terrace', l.outdoor_surface || (l.outdoor_terrace ? 'Yes' : null)],
    ['Garden', l.outdoor_garden ? 'Yes' : null],
  ].filter(([, v]) => v)
})
</script>

<template>
  <div class="detail-panel">
    <div>
      <div class="detail-header">
        <div>
          <div class="detail-kicker">Property details</div>
          <h2>{{ fmtPrice(listing.price) }} {{ typeLabel(listing.property_type) }}</h2>
          <div class="detail-subtitle">{{ listing.postcode || 'Location unavailable' }} · {{ listing.source || 'Unknown portal' }}</div>
        </div>
        <a :href="listing.url" target="_blank" class="btn btn-primary btn-sm">Open on portal ↗</a>
      </div>
      <div class="detail-metrics">
        <div class="detail-metric">
          <div class="detail-metric-label">Price</div>
          <div class="detail-metric-value">{{ fmtPrice(listing.price) }}</div>
        </div>
        <div class="detail-metric">
          <div class="detail-metric-label">Surface</div>
          <div class="detail-metric-value">{{ listing.surface_area || '?' }} m²</div>
        </div>
        <div class="detail-metric">
          <div class="detail-metric-label">Beds</div>
          <div class="detail-metric-value">{{ listing.bedrooms || '?' }}</div>
        </div>
        <div class="detail-metric">
          <div class="detail-metric-label">EPC</div>
          <div class="detail-metric-value" :style="{ color: EPC_COLORS[listing.epc_score] }">{{ listing.epc_score || '?' }}</div>
        </div>
      </div>

      <div v-if="listing._score !== null" class="score-section">
        <div class="score-title" :style="{ color: scoreColor(listing._score) }">
          Score {{ Math.round(listing._score) }} / 100
        </div>
        <div v-for="comp in SCORE_COMPONENTS" :key="comp.key">
          <div class="score-row">
            <span>{{ comp.label }}</span>
            <span class="score-val">{{ Math.round(listing._components?.[comp.key] || 0) }} / {{ comp.max }}</span>
          </div>
          <div class="progress-bar-wrap">
            <div class="progress-bar-fill" :style="{ width: Math.min(100, ((listing._components?.[comp.key] || 0) / comp.max) * 100) + '%' }"></div>
          </div>
        </div>
      </div>

      <div v-else style="background:#FFF1F3;color:#C01048;border-radius:6px;padding:0.5rem 0.75rem;font-size:0.8rem;margin-bottom:1rem">
        Excluded: {{ (listing._exclusions || []).join(', ') || 'fails hard filters' }}
      </div>

    </div>

    <div>
      <div v-if="images.length" class="detail-gallery">
        <button class="gallery-image-button" type="button" @click="modalOpen = true" :aria-label="`Open image ${imageIdx + 1} larger`">
          <img :src="images[imageIdx]" :alt="listing.source" />
        </button>
        <div v-if="images.length > 1" class="gallery-thumbs" role="list" aria-label="Property images">
          <button v-for="(image, idx) in images" :key="image + idx" type="button" :class="['gallery-thumb', { active: idx === imageIdx }]" @click="imageIdx = idx" :aria-label="`Show image ${idx + 1}`">
            <img :src="image" alt="" />
          </button>
        </div>
        <div v-if="images.length > 1" class="gallery-nav">
          <button class="btn btn-secondary btn-sm" @click="imageIdx = (imageIdx - 1 + images.length) % images.length">‹ Prev</button>
          <button class="btn btn-secondary btn-sm" @click="imageIdx = (imageIdx + 1) % images.length">Next ›</button>
          <span class="gallery-caption">{{ imageIdx + 1 }} / {{ images.length }}</span>
        </div>
      </div>

      <div v-if="modalOpen" class="image-modal" role="dialog" aria-modal="true" @click.self="modalOpen = false">
        <button class="image-modal-close" type="button" aria-label="Close image" @click="modalOpen = false">×</button>
        <img :src="images[imageIdx]" :alt="listing.source" />
      </div>

      <table class="detail-table">
        <tr v-for="[k, v] in details" :key="k">
          <td>{{ k }}</td>
          <td>{{ v }}</td>
        </tr>
      </table>

      <div v-if="listing.description_english || listing.description" class="detail-desc">
        {{ descriptionText(listing) }}
      </div>
    </div>
  </div>
</template>
