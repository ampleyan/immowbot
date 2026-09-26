<script setup>
import { ref } from 'vue'
import { formatListingAddress, formatListingDate, isNewToCheck, listingAge, potentialBenefits } from '../views/listingUtils.js'
import { formatScorePoints, scoreBand, scoreCardClass, scoreComponentRows } from '../views/scorePresentation.js'
import { api } from '../api.js'

const props = defineProps(['listing', 'isSaving', 'isChecked', 'showSelect', 'selected'])
const emit = defineEmits(['toggle-select', 'toggle-detail', 'toggle-save', 'quick-status', 'reject', 'updated', 'contact'])

const currentImgIdx = ref(0)

function contactPhone(listing) {
  return listing._workflow?.agent_phone || listing.agent_phone || ''
}

function contactEmail(listing) {
  return listing._workflow?.agent_email || listing.agent_email || ''
}

function phoneHref(value) {
  return value.trim().replace(/[^\d+*#;]/g, '')
}

function emailHref(value) {
  return encodeURIComponent(value.trim()).replace(/%40/gi, '@')
}

function cardImages(listing) {
  const d = listing.all_property_details || {}
  const seen = new Set()
  return [
    listing.image_url_1, listing.image_url_2,
    d['Image 1 URL'], d['Image 2 URL'], d['Image 3 URL'],
    ...(Array.isArray(listing.images) ? listing.images : []),
  ].filter(u => typeof u === 'string' && u.startsWith('http') && !seen.has(u) && seen.add(u))
}

function stepImg(dir, e) {
  e.stopPropagation()
  const imgs = cardImages(props.listing)
  currentImgIdx.value = (currentImgIdx.value + dir + imgs.length) % imgs.length
}

const noteOpen = ref(false)
const note = ref(props.listing._note || '')
let noteSaveTimer = null

const rejecting = ref(false)
const rejectNote = ref('')

function toggleReject(e) {
  e.stopPropagation()
  rejecting.value = !rejecting.value
  rejectNote.value = ''
  if (rejecting.value) noteOpen.value = false
}

function confirmReject(e) {
  e.stopPropagation()
  emit('reject', rejectNote.value)
  rejecting.value = false
  rejectNote.value = ''
}

const rating = ref(props.listing._workflow?.rating || 0)
const hoverRating = ref(0)
const ratingSaving = ref(false)
const ratingJustSaved = ref(false)

async function setRating(n) {
  rating.value = rating.value === n ? 0 : n
  ratingSaving.value = true
  try {
    await api.saveWorkflow(props.listing.source, props.listing.source_listing_id, { ...(props.listing._workflow || {}), rating: rating.value || null })
    ratingJustSaved.value = true
    setTimeout(() => { ratingJustSaved.value = false }, 900)
    emit('updated')
  } catch {}
  ratingSaving.value = false
}

const pendingAction = ref(null)
function triggerActionFeedback(action, cb) {
  pendingAction.value = action
  cb()
  setTimeout(() => { pendingAction.value = null }, 350)
}

function toggleNote(e) {
  e.stopPropagation()
  noteOpen.value = !noteOpen.value
}

function scheduleNoteSave() {
  clearTimeout(noteSaveTimer)
  noteSaveTimer = setTimeout(async () => {
    try {
      await api.saveNote(props.listing.source, props.listing.source_listing_id, note.value)
      emit('updated')
    } catch {}
  }, 800)
}

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
  return `pill ${scoreCardClass(score)}`
}

function scoreLabel(score) {
  if (score === null || score === undefined) return '—'
  return Math.round(score)
}

function scoreHighlights(listing) {
  if (listing._score === null || listing._score === undefined || !listing._components) return []
  return scoreComponentRows(listing)
    .filter(component => component.points !== 0)
    .sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
    .slice(0, 3)
    .map(component => ({ ...component, value: formatScorePoints(component.points) }))
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
  const floor = (l.all_property_details || {})['Floor']
  if (floor != null) parts.push(`floor ${floor}`)
  if (l.postcode) parts.push(l.postcode)
  return parts.join(' · ') || '—'
}

function outdoorFeatures(l) {
  const features = []
  if (l.outdoor_terrace || l.outdoor_surface) features.push(l.outdoor_surface ? `Terrace ${Math.round(l.outdoor_surface)} m²` : 'Terrace')
  if (l.outdoor_garden) features.push('Garden')
  return features
}

function fmtUpdatedAt(iso) {
  if (!iso) return null
  const d = new Date(iso)
  const diffMs = Date.now() - d.getTime()
  const diffH = diffMs / 3600000
  if (diffH < 1) return 'updated just now'
  if (diffH < 24) return `updated ${Math.floor(diffH)}h ago`
  const diffD = Math.floor(diffH / 24)
  if (diffD === 1) return 'updated yesterday'
  if (diffD < 7) return `updated ${diffD}d ago`
  return `updated ${d.toLocaleDateString('en-BE', { day: 'numeric', month: 'short' })}`
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
    :class="['card', { checked: isChecked, excluded: listing._exclusions?.length > 0, selected, 'no-select': showSelect === false, 'new-to-check': isNewToCheck(listing) }]"
    @click="emit('toggle-detail')"
  >
    <div class="card-inner">
      <div v-if="showSelect !== false" class="card-checkbox">
        <input type="checkbox" :checked="isChecked" :aria-label="`Select ${formatListingAddress(listing)}`" @click.stop @keydown.stop @change="emit('toggle-select')" />
      </div>

      <div v-if="!selected" class="card-img" @click.stop @keydown.stop>
        <template v-if="cardImages(listing).length">
          <img :src="cardImages(listing)[currentImgIdx]" :alt="listing.source" loading="lazy" />
          <template v-if="cardImages(listing).length > 1">
            <button class="card-carousel-btn card-carousel-prev" type="button" aria-label="Previous property photo" @click="stepImg(-1, $event)">‹</button>
            <button class="card-carousel-btn card-carousel-next" type="button" aria-label="Next property photo" @click="stepImg(1, $event)">›</button>
            <div class="card-carousel-dots">
              <i v-for="(_, i) in cardImages(listing)" :key="i" :class="['card-carousel-dot', { active: i === currentImgIdx }]"></i>
            </div>
          </template>
        </template>
        <div v-else class="card-img-placeholder">🏠</div>
        <div :class="['card-score-overlay', scoreClass(listing._score)]" :aria-label="listing._score == null ? 'Score unavailable' : `Score ${scoreLabel(listing._score)} out of 100, ${scoreBand(listing._score)?.label}`">
          <span>{{ scoreBand(listing._score)?.shortLabel || 'No score' }}</span>
          <strong>{{ scoreLabel(listing._score) }}</strong>
        </div>
      </div>

      <div class="card-data">
        <div class="card-price-row">
          <span class="card-price">{{ fmtPrice(listing.price) }}</span>
          <span class="card-type">{{ (listing.property_type || '').replace(/^\w/, c => c.toUpperCase()) }}</span>
        </div>
        <div class="card-specs">{{ specs(listing) }}</div>
        <button class="card-address card-open-detail" type="button" :data-listing-url="listing.url" :aria-label="`View details for ${formatListingAddress(listing)}`" @click.stop="emit('toggle-detail')">{{ formatListingAddress(listing) }}</button>
        <div class="card-id">
          <span v-if="listing.source_listing_id">ID: {{ listing.source_listing_id }}</span>
          <span v-if="formatListingDate(listing.source_created_at)" class="card-scraped-at">Ad {{ formatListingDate(listing.source_created_at) }}</span>
          <span v-if="formatListingDate(listing._first_seen_at)" class="card-scraped-at">Scraped {{ formatListingDate(listing._first_seen_at) }}</span>
          <span v-if="listingAge(listing)" class="card-scraped-at">{{ listingAge(listing).label }} {{ listingAge(listing).days }} {{ listingAge(listing).days === 1 ? 'day' : 'days' }}</span>
          <span v-if="fmtUpdatedAt(listing._last_updated_at)" class="card-scraped-at">{{ fmtUpdatedAt(listing._last_updated_at) }}</span>
        </div>
        <div v-if="scoreHighlights(listing).length" class="card-score-summary" aria-label="Score highlights">
            <span v-for="component in scoreHighlights(listing)" :key="component.key" :class="component.points < 0 ? 'score-highlight-negative' : 'score-highlight-positive'">
            {{ component.label }} {{ component.value }}
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
          <span v-if="listing._availability_status === 'gone'" class="pill pill-red">GONE</span>
          <span v-if="isNewToCheck(listing)" class="pill pill-new">NEW TO CHECK</span>
          <span v-if="listing._exclusions?.length" class="pill pill-red">excluded</span>
          <span v-if="listing.under_option" class="pill pill-under-option">UNDER OPTION</span>
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
        <a v-if="contactPhone(listing)" class="card-action-btn btn-ghost" :href="`tel:${phoneHref(contactPhone(listing))}`" :aria-label="`Call ${contactPhone(listing)}`" title="Call" @click.stop>☎</a>
        <a v-if="contactEmail(listing)" class="card-action-btn btn-ghost" :href="`mailto:${emailHref(contactEmail(listing))}`" :aria-label="`Email ${contactEmail(listing)}`" title="Email" @click.stop>✉</a>
        <button v-if="!contactPhone(listing) && !contactEmail(listing)" class="card-action-btn btn-ghost" type="button" title="Add contact details" aria-label="Add contact details" @click.stop="emit('contact')">☎</button>
        <button :class="['card-action-btn', 'btn-ghost', { 'action-pending': pendingAction === 'save' }]" :aria-label="isSaving ? 'Close lists' : 'Add to list'" :title="isSaving ? 'Close lists' : 'Add to list'" @click.stop="triggerActionFeedback('save', () => emit('toggle-save'))">{{ isSaving ? '×' : '+' }}</button>
        <button :class="['card-action-btn', listing._workflow?.status === 'Interested' ? 'btn-interested' : 'btn-ghost', { 'action-pending': pendingAction === 'interested' }]" type="button" aria-label="Mark as interested" :aria-pressed="listing._workflow?.status === 'Interested'" title="Interested" @click.stop="triggerActionFeedback('interested', () => emit('quick-status', 'Interested'))">♥</button>
        <button :class="['card-action-btn', note ? 'btn-yellow' : 'btn-ghost']" type="button" :aria-label="noteOpen ? 'Close property note' : 'Add property note'" :title="noteOpen ? 'Close note' : 'Add note'" @click.stop="toggleNote">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M2 2h12v9H9l-3 3v-3H2V2zm1 1v7h3v2l2-2h5V3H3z"/></svg>
        </button>
        <button :class="['card-action-btn', listing._workflow?.status === 'Rejected' || rejecting ? 'btn-red' : 'btn-ghost', { 'action-pending': pendingAction === 'reject' }]" type="button" aria-label="Reject property" :aria-pressed="listing._workflow?.status === 'Rejected' || rejecting" title="Reject" @click.stop="(e) => { triggerActionFeedback('reject', () => {}); toggleReject(e) }">×</button>
        <div :class="['card-rating', { 'is-saving': ratingSaving }]" role="group" aria-label="Rate this property" @click.stop @mouseleave="hoverRating = 0">
          <button v-for="n in 5" :key="n" :class="['rating-star', { filled: n <= (hoverRating || rating) }]" type="button" @mouseenter="hoverRating = n" @click.stop="setRating(n)" :aria-label="`Rate ${n} out of 5 stars`" :aria-pressed="rating === n" :title="`${n} star${n > 1 ? 's' : ''}`">{{ n <= (hoverRating || rating) ? '★' : '☆' }}</button>
          <span v-if="ratingJustSaved" class="card-rating-saved-badge">✓</span>
        </div>
      </div>
    </div>
    <div v-if="noteOpen" class="card-note-wrap" @click.stop @keydown.stop>
      <label class="visually-hidden" :for="`property-note-${listing.source_listing_id}`">Note for {{ formatListingAddress(listing) }}</label>
      <textarea :id="`property-note-${listing.source_listing_id}`" class="card-note-input" v-model="note" rows="2" placeholder="Add a note…" @input="scheduleNoteSave" autofocus></textarea>
    </div>
    <div v-if="rejecting" class="card-note-wrap" @click.stop @keydown.stop>
      <label class="visually-hidden" :for="`property-rejection-${listing.source_listing_id}`">Reason for rejecting {{ formatListingAddress(listing) }}</label>
      <textarea :id="`property-rejection-${listing.source_listing_id}`" class="card-note-input" v-model="rejectNote" rows="2" placeholder="Reason for rejection (optional)…" autofocus></textarea>
      <div class="card-reject-confirm">
        <button class="btn btn-ghost btn-sm" @click.stop="rejecting = false">Cancel</button>
        <button class="btn btn-sm card-reject-btn" @click="confirmReject">Confirm rejection</button>
      </div>
    </div>
  </div>
</template>
