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

const details = computed(() => {
  const l = props.listing
  return [
    ['Postcode', l.postcode],
    ['Type', (l.property_type || '').replace(/^\w/, c => c.toUpperCase())],
    ['Portal', l.source],
    ['Built', l.construction_year],
    ['Terrace', l.outdoor_surface || (l.outdoor_terrace ? 'Yes' : null)],
  ].filter(([, v]) => v)
})
</script>

<template>
  <div class="detail-panel">
    <div>
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

      <a :href="listing.url" target="_blank" class="btn btn-primary btn-sm">Open on portal ↗</a>
    </div>

    <div>
      <div v-if="images.length">
        <img :src="images[imageIdx]" :alt="listing.source" />
        <div v-if="images.length > 1" class="gallery-nav">
          <button class="btn btn-secondary btn-sm" @click="imageIdx = (imageIdx - 1 + images.length) % images.length">‹ Prev</button>
          <button class="btn btn-secondary btn-sm" @click="imageIdx = (imageIdx + 1) % images.length">Next ›</button>
          <span class="gallery-caption">{{ imageIdx + 1 }} / {{ images.length }}</span>
        </div>
      </div>

      <table class="detail-table">
        <tr v-for="[k, v] in details" :key="k">
          <td>{{ k }}</td>
          <td>{{ v }}</td>
        </tr>
      </table>

      <div v-if="listing.description_english || listing.description" class="detail-desc">
        {{ (listing.description_english || listing.description || '').slice(0, 600) }}
      </div>
    </div>
  </div>
</template>
