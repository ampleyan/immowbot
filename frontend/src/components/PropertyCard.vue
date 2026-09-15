<script setup>
import { formatListingAddress, isNewListing, potentialBenefits } from '../views/listingUtils.js'

defineProps(['listing', 'isSaving', 'isChecked', 'showSelect'])
const emit = defineEmits(['toggle-select', 'toggle-detail', 'toggle-save', 'quick-status'])

const SCORE_COMPONENTS = [
  { key: 'price', label: 'Price', max: 30 },
  { key: 'surface_area', label: 'Surface', max: 25 },
  { key: 'bedrooms', label: 'Bedrooms', max: 15 },
  { key: 'epc', label: 'EPC', max: 20 },
  { key: 'completeness', label: 'Completeness', max: 10 },
  { key: 'outdoor', label: 'Outdoor', max: 5 },
]

function fmtPrice(p) {
  if (!p) return '—'
  return '€' + Math.round(p).toLocaleString('nl-BE')
}

function epcClass(score) {
  return ['A++', 'A+', 'A', 'B'].includes(score) ? 'epc-green' : score === 'C' ? 'epc-yellow' : 'epc-red'
}

function getImage(listing) {
  const d = listing.all_property_details || {}
  const candidates = [
    listing.image_url_1, listing.image_url_2,
    d['Image 1 URL'], d['Image 2 URL'],
    ...(Array.isArray(listing.images) ? listing.images : []),
  ]
  return candidates.find(u => typeof u === 'string' && u.startsWith('http')) || null
}

function scoreClass(score) {
  if (score === null || score === undefined) return 'pill pill-neutral'
  if (score >= 80) return 'pill pill-green'
  if (score >= 60) return 'pill pill-yellow'
  return 'pill pill-red'
}

function scoreLabel(score) {
  if (score === null || score === undefined) return '—'
  return Math.round(score)
}

function scoreHighlights(listing) {
  if (listing._score === null || listing._score === undefined || !listing._components) return []
  return SCORE_COMPONENTS
    .map(component => ({
      ...component,
      value: Math.round(Number(listing._components[component.key]) || 0),
    }))
    .filter(component => component.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 3)
    .map(component => ({ ...component, percentage: Math.min(100, Math.round((component.value / component.max) * 100)) }))
}

function scoreHighlightClass(percentage) {
  if (percentage >= 80) return 'score-highlight-high'
  if (percentage >= 60) return 'score-highlight-medium'
  return 'score-highlight-low'
}

function descriptionSnippet(listing) {
  const raw = listing.description_english || listing.description || ''
  const readable = String(raw)
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return readable.length > 300 ? `${readable.slice(0, 300).trimEnd()}…` : readable
}

function specs(l) {
  const parts = []
  if (l.bedrooms) parts.push(`${Math.round(l.bedrooms)} bd`)
  if (l.surface_area) parts.push(`${Math.round(l.surface_area)} m²`)
  if (l.postcode) parts.push(l.postcode)
  return parts.join(' · ') || '—'
}

function outdoorFeatures(l) {
  const features = []
  if (l.outdoor_terrace || l.outdoor_surface) features.push(l.outdoor_surface ? `Terrace ${Math.round(l.outdoor_surface)} m²` : 'Terrace')
  if (l.outdoor_garden) features.push('Garden')
  return features
}

function fmtScrapedAt(iso) {
  if (!iso) return null
  const d = new Date(iso)
  const diffMs = Date.now() - d.getTime()
  const diffH = diffMs / 3600000
  if (diffH < 1) return 'scraped just now'
  if (diffH < 24) return `scraped ${Math.floor(diffH)}h ago`
  const diffD = Math.floor(diffH / 24)
  if (diffD === 1) return 'scraped yesterday'
  if (diffD < 7) return `scraped ${diffD}d ago`
  return `scraped ${d.toLocaleDateString('en-BE', { day: 'numeric', month: 'short' })}`
}

function hasParking(l) {
  const d = l.all_property_details || {}
  return !!(d['Garage'] || d['Parking indoor'] || d['Parking outdoor'] || d['Parking closed box'] || l.garage || l.parking)
}

function followUpAlert(l) {
  const date = l._workflow?.next_follow_up_date
  if (!date) return null
  const today = new Date().toISOString().slice(0, 10)
  if (date < today) return { label: `Follow-up overdue · ${date}`, overdue: true }
  if (date === today) return { label: 'Follow-up today', overdue: false }
  return null
}
</script>

<template>
  <div
    :class="['card', { checked: isChecked, excluded: listing._score === null, 'no-select': showSelect === false }]"
    role="button"
    tabindex="0"
    @click="emit('toggle-detail')"
    @keydown.enter.prevent="emit('toggle-detail')"
    @keydown.space.prevent="emit('toggle-detail')"
  >
    <div class="card-inner">
      <div v-if="showSelect !== false" class="card-checkbox">
        <input type="checkbox" :checked="isChecked" @click.stop @keydown.stop @change="emit('toggle-select')" />
      </div>

      <div class="card-img">
        <img v-if="getImage(listing)" :src="getImage(listing)" :alt="listing.source" loading="lazy" />
        <div v-else class="card-img-placeholder">🏠</div>
      </div>

      <div class="card-data">
        <div class="card-price-row">
          <span class="card-price">{{ fmtPrice(listing.price) }}</span>
          <span class="card-type">{{ (listing.property_type || '').replace(/^\w/, c => c.toUpperCase()) }}</span>
          <span class="card-score-badge">
            <span :class="scoreClass(listing._score)">{{ scoreLabel(listing._score) }}</span>
          </span>
        </div>
        <div class="card-specs">{{ specs(listing) }}</div>
        <div class="card-address">{{ formatListingAddress(listing) }}</div>
        <div class="card-id">
          <span v-if="listing.source_listing_id">ID: {{ listing.source_listing_id }}</span>
          <span v-if="fmtScrapedAt(listing._last_seen_at)" class="card-scraped-at">{{ fmtScrapedAt(listing._last_seen_at) }}</span>
        </div>
        <div v-if="scoreHighlights(listing).length" class="card-score-summary" aria-label="Score highlights">
          <span v-for="component in scoreHighlights(listing)" :key="component.key" :class="scoreHighlightClass(component.percentage)">
            {{ component.label }} {{ component.percentage }}%
          </span>
        </div>
        <div v-if="followUpAlert(listing)" :class="['card-followup-alert', { overdue: followUpAlert(listing).overdue }]">
          {{ followUpAlert(listing).overdue ? '⚠' : '🔔' }} {{ followUpAlert(listing).label }}
        </div>
        <div v-if="listing._smart_list_reason" class="card-smart-reason">{{ listing._smart_list_reason }}</div>
        <div class="card-badges">
          <span v-if="listing.epc_score" :class="['pill-epc', epcClass(listing.epc_score)]">
            EPC {{ listing.epc_score }}
          </span>
          <span class="pill pill-neutral">{{ listing.source }}</span>
          <span v-if="isNewListing(listing)" class="pill pill-new">new</span>
          <span v-if="listing._score === null" class="pill pill-red">excluded</span>
          <span v-if="listing.under_option" class="pill pill-yellow">under option</span>
          <span v-if="listing._price_reduced" class="pill pill-green">↓ price reduced</span>
          <span v-if="listing.has_tenant" class="pill pill-yellow">tenant in place</span>
          <span v-if="listing.monthly_charges" class="pill pill-neutral">€{{ Math.round(listing.monthly_charges) }}/mo charges</span>
          <span v-if="hasParking(listing)" class="pill pill-neutral">🅿 parking</span>
          <span v-for="benefit in potentialBenefits(listing)" :key="benefit" class="pill pill-benefit">✦ {{ benefit }}</span>
          <span v-for="feature in outdoorFeatures(listing)" :key="feature" class="pill pill-outdoor">🌿 {{ feature }}</span>
          <span v-if="listing._list_ids && listing._list_ids.length" class="pill pill-blue">saved</span>
          <span v-if="listing._note" class="pill pill-green">note</span>
        </div>
      </div>

      <div class="card-desc">
        {{ descriptionSnippet(listing) }}
      </div>

      <div class="card-actions">
        <button class="btn btn-secondary btn-sm card-icon-action list-action" :aria-label="isSaving ? 'Close lists' : 'Add to list'" :title="isSaving ? 'Close lists' : 'Add to list'" @click.stop="emit('toggle-save')">
          {{ isSaving ? '×' : '+' }}
        </button>
        <button class="btn btn-secondary btn-sm card-icon-action quick-shortlist" aria-label="Add to shortlist" title="Add to shortlist" @click.stop="emit('quick-status', 'Interested')">★</button>
        <button class="btn btn-ghost btn-sm card-icon-action quick-reject" aria-label="Reject listing" title="Reject listing" @click.stop="emit('quick-status', 'Rejected')">×</button>
      </div>
    </div>
  </div>
</template>
