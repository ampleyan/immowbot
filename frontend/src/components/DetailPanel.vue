<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { api } from '../api.js'
import { formatListingAddress, formatListingDate } from '../views/listingUtils.js'

const props = defineProps(['listing'])
const emit = defineEmits(['updated'])

const EPC_COLORS = {
  'A++': '#006B3C', 'A+': '#006B3C', 'A': '#006B3C',
  'B': '#2D8A4E', 'C': '#7AB648',
  'D': '#F5C400', 'E': '#F0A500',
  'F': '#D93E1F', 'G': '#9B1B0E',
}

const SCORE_COMPONENTS = [
  { key: 'price', label: 'Price', fallbackMax: 30 },
  { key: 'surface_area', label: 'Surface', fallbackMax: 25 },
  { key: 'bedrooms', label: 'Bedrooms', fallbackMax: 15 },
  { key: 'epc', label: 'EPC', fallbackMax: 20 },
  { key: 'completeness', label: 'Completeness', fallbackMax: 10 },
  { key: 'outdoor', label: 'Outdoor', fallbackMax: 5 },
]

const imageIdx = ref(0)
const modalOpen = ref(false)
const changes = ref([])
const interactions = ref([])
const workflow = ref({ status: 'New', contact_date: '', next_follow_up_date: '', agent_name: '', agent_phone: '', agent_email: '', offer_amount: null, rating: null })
const workflowSaving = ref(false)
const interactionKind = ref('call')
const interactionNote = ref('')
const interactionFollowUp = ref('')
const interactionSaving = ref(false)
const interactionError = ref('')
const contactCopied = ref(false)
const detailHoverRating = ref(0)

async function loadChanges() {
  try { changes.value = (await api.getListingChanges(props.listing.source, props.listing.source_listing_id)).changes || [] } catch { changes.value = [] }
}

onMounted(loadChanges)
watch(() => props.listing.source + ':' + props.listing.source_listing_id, loadChanges)

async function loadInteractions() {
  try { interactions.value = await api.getInteractions(props.listing.source, props.listing.source_listing_id) } catch { interactions.value = [] }
}

onMounted(loadInteractions)
watch(() => props.listing.source + ':' + props.listing.source_listing_id, loadInteractions)

async function loadWorkflow() {
  try { workflow.value = { ...workflow.value, ...(await api.getWorkflow(props.listing.source, props.listing.source_listing_id)) } } catch {}
  if (!workflow.value.agent_name) workflow.value.agent_name = props.listing.agent_name || ''
  if (!workflow.value.agent_phone) workflow.value.agent_phone = props.listing.agent_phone || ''
  if (!workflow.value.agent_email) workflow.value.agent_email = props.listing.agent_email || ''
}

async function saveWorkflow() {
  workflowSaving.value = true
  try { workflow.value = await api.saveWorkflow(props.listing.source, props.listing.source_listing_id, workflow.value); emit('updated') } catch {}
  workflowSaving.value = false
}

async function logInteraction() {
  if (!interactionNote.value.trim()) return
  interactionSaving.value = true
  interactionError.value = ''
  try {
    const interaction = await api.addInteraction(props.listing.source, props.listing.source_listing_id, {
      kind: interactionKind.value,
      note: interactionNote.value.trim(),
      next_follow_up_date: interactionFollowUp.value || null,
    })
    interactions.value = [interaction, ...interactions.value]
    if (interactionFollowUp.value && workflow.value.next_follow_up_date !== interactionFollowUp.value) {
      workflow.value = await api.saveWorkflow(props.listing.source, props.listing.source_listing_id, { ...workflow.value, next_follow_up_date: interactionFollowUp.value })
      emit('updated')
    }
    interactionNote.value = ''
    interactionFollowUp.value = ''
  } catch {
    interactionError.value = 'Could not save this interaction.'
  }
  interactionSaving.value = false
}

async function prepareInteraction(kind) {
  interactionKind.value = kind
  await nextTick()
  document.querySelector('.interaction-note')?.focus()
}

async function copyContact() {
  const details = [agentName.value, agentPhone.value, agentEmail.value].filter(Boolean).join(' · ')
  if (!details || !navigator.clipboard) return
  await navigator.clipboard.writeText(details)
  contactCopied.value = true
  setTimeout(() => { contactCopied.value = false }, 2000)
}

const agentName = computed(() => workflow.value.agent_name || props.listing.agent_name)
const agentPhone = computed(() => workflow.value.agent_phone || props.listing.agent_phone)
const agentEmail = computed(() => workflow.value.agent_email || props.listing.agent_email)

const agentMailto = computed(() => {
  const email = agentEmail.value
  if (!email) return null
  const address = formatListingAddress(props.listing)
  const price = props.listing.price ? `€${Math.round(props.listing.price).toLocaleString('nl-BE')}` : ''
  const subject = `Te koop - ${address}`
  const body = [
    `Goedag,`,
    ``,
    `Ik ben geïnteresseerd in uw eigendom te koop aan ${address}${price ? ` (${price})` : ''}.`,
    props.listing.url ? `${props.listing.url}` : '',
    ``,
    `Zou het mogelijk zijn een afspraak te maken voor een bezichtiging?`,
    ``,
    `Met vriendelijke groeten,`,
  ].filter(line => line !== null).join('\n')
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
})

onMounted(loadWorkflow)
watch(() => props.listing.source + ':' + props.listing.source_listing_id, loadWorkflow)

const note = ref(props.listing._note || '')
const noteSaving = ref(false)
const noteSaved = ref(false)
let noteSaveTimer = null

async function loadNote() {
  try { note.value = (await api.getNote(props.listing.source, props.listing.source_listing_id)).note || '' } catch {}
}

async function saveNote() {
  noteSaving.value = true
  try {
    await api.saveNote(props.listing.source, props.listing.source_listing_id, note.value)
    noteSaved.value = true
    setTimeout(() => { noteSaved.value = false }, 1500)
  } catch {}
  noteSaving.value = false
}

function scheduleNoteSave() {
  clearTimeout(noteSaveTimer)
  noteSaveTimer = setTimeout(saveNote, 800)
}

onMounted(loadNote)
watch(() => props.listing.source + ':' + props.listing.source_listing_id, loadNote)

const images = computed(() => {
  const l = props.listing
  const d = l.all_property_details || {}
  const detailImages = Object.entries(d)
    .filter(([key, value]) => /^Image \d+ URL$/i.test(key) && value)
    .map(([, value]) => value)
  const candidates = [
    l.image_url_1, l.image_url_2,
    ...(Array.isArray(l.images) ? l.images : []),
    ...detailImages,
  ]
  return [...new Set(candidates.filter(u => typeof u === 'string' && u.startsWith('http')))]
})

const mapsUrl = computed(() => {
  const l = props.listing
  if (l.latitude && l.longitude)
    return `https://www.google.com/maps?q=${l.latitude},${l.longitude}`
  const query = [l.street, l.city, l.postcode, 'Belgium'].filter(Boolean).join(' ')
  return `https://www.google.com/maps/search/${encodeURIComponent(query)}`
})

function fmtPrice(p) {
  if (p === null || p === undefined || p === '') return '—'
  return '€' + Math.round(p).toLocaleString('nl-BE')
}

function hasFactValue(value) {
  return value !== null && value !== undefined && !(typeof value === 'string' && !value.trim())
}

function formatBoolean(value, positive = 'Yes', negative = 'No') {
  return value ? positive : negative
}

function formatArea(value) {
  return `${value} m²`
}

function formatEpcValue(value) {
  return typeof value === 'number' ? `${value} kWh/m²/year` : String(value)
}

function makeFact(label, source, value = source, extra = {}) {
  return hasFactValue(source) ? { label, value, ...extra } : null
}

const contactStatus = computed(() => ({
  available: 'Contact available',
  unavailable: 'Contact unavailable',
  requires_login: 'Requires login',
  reveal_failed: 'Contact reveal failed',
}[props.listing.contact_status]))

const factGroups = computed(() => {
  const l = props.listing
  return [
    {
      title: 'Property',
      facts: [
        makeFact('Bathrooms', l.bathrooms),
        makeFact('Floor', l.floor),
        makeFact('Parking', l.parking, typeof l.parking === 'number' ? `${l.parking} spaces` : l.parking),
        makeFact('Terrace', l.terrace, typeof l.terrace === 'number' ? formatArea(l.terrace) : formatBoolean(l.terrace)),
        makeFact('Garden', l.garden, formatBoolean(l.garden)),
        makeFact('Solar panels', l.solar_panels, formatBoolean(l.solar_panels)),
        makeFact('Investment property', l.investment_property, formatBoolean(l.investment_property)),
        makeFact('New build', l.new_build, formatBoolean(l.new_build)),
      ].filter(Boolean),
    },
    {
      title: 'Energy',
      facts: [
        makeFact('EPC value', l.epc_value, formatEpcValue(l.epc_value)),
        makeFact('EPC certificate', l.epc_certificate_number),
        makeFact('Heating', l.heating_type),
        makeFact('Renovation obligation', l.renovation_obligation, formatBoolean(l.renovation_obligation, 'Required', 'Not required')),
        makeFact('Renovation year', l.renovation_year),
      ].filter(Boolean),
    },
    {
      title: 'Costs & legal',
      facts: [
        makeFact('Monthly charges', l.monthly_charges, `${fmtPrice(l.monthly_charges)} / month`),
        makeFact('Cadastral income', l.cadastral_income, fmtPrice(l.cadastral_income)),
        makeFact('P-score', l.p_score),
        makeFact('G-score', l.g_score),
      ].filter(Boolean),
    },
    {
      title: 'Agency',
      facts: [
        makeFact('Agency', l.agency_name),
        makeFact('Address', l.agency_address),
        makeFact('Website', l.agency_url, l.agency_url, { href: l.agency_url, className: 'agency-website' }),
      ].filter(Boolean),
    },
    {
      title: 'Contact',
      facts: [
        makeFact('Name', agentName.value),
        makeFact('Phone', agentPhone.value, agentPhone.value, { href: agentPhone.value ? `tel:${agentPhone.value}` : null }),
        makeFact('Email', agentEmail.value, agentEmail.value, { href: agentMailto.value }),
        makeFact('Published', l.source_created_at, formatListingDate(l.source_created_at)),
        makeFact('Source updated', l.source_updated_at, formatListingDate(l.source_updated_at)),
        makeFact('Contact checked', l.contact_scraped_at, formatListingDate(l.contact_scraped_at)),
        makeFact('Status', contactStatus.value, contactStatus.value, { className: 'contact-status' }),
      ].filter(Boolean),
    },
  ].filter(group => group.facts.length)
})

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
  ].filter(([, v]) => v)
})

function componentMax(component) {
  return props.listing._score_weights?.[component.key] ?? component.fallbackMax
}

function componentPercent(component) {
  const max = componentMax(component)
  const value = Number(props.listing._components?.[component.key]) || 0
  return Math.round(Math.min(100, Math.max(0, (value / max) * 100)))
}

function interactionLabel(kind) {
  return { call: 'Call', email: 'Email', message: 'Message', visit: 'Visit', status: 'Status update', other: 'Other' }[kind] || kind
}

function interactionDate(value) {
  return new Date(value).toLocaleString('en-BE', { dateStyle: 'medium', timeStyle: 'short' })
}
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
        <div style="display:flex;gap:0.4rem;align-items:center">
          <a :href="mapsUrl" target="_blank" class="btn btn-secondary btn-sm" title="Open in Google Maps">📍</a>
          <a :href="listing.url" target="_blank" class="btn btn-primary btn-sm">Open on portal ↗</a>
        </div>
      </div>
      <div v-if="agentPhone || agentEmail" class="contact-actions">
        <a v-if="agentPhone" class="btn btn-secondary btn-sm contact-phone" :href="`tel:${agentPhone}`" @click="prepareInteraction('call')">Call {{ agentName || 'agent' }}</a>
        <a v-if="agentMailto" class="btn btn-secondary btn-sm contact-email" :href="agentMailto" @click="prepareInteraction('email')">Email</a>
        <button type="button" class="btn btn-ghost btn-sm copy-contact" @click="copyContact">{{ contactCopied ? 'Copied' : 'Copy contact' }}</button>
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

      <div v-if="factGroups.length" class="detail-facts">
        <section v-for="group in factGroups" :key="group.title" class="detail-fact-group">
          <h3>{{ group.title }}</h3>
          <dl>
            <div v-for="fact in group.facts" :key="fact.label" class="detail-fact-row">
              <dt>{{ fact.label }}</dt>
              <dd :class="fact.className">
                <a v-if="fact.href" :href="fact.href" :class="fact.className" :target="fact.href.startsWith('http') ? '_blank' : null">{{ fact.value }}</a>
                <template v-else>{{ fact.value }}</template>
              </dd>
            </div>
          </dl>
        </section>
      </div>

      <div v-if="listing._exclusions?.length" style="background:#FFF1F3;color:#C01048;border-radius:6px;padding:0.35rem 0.75rem;font-size:0.8rem;margin-bottom:0.5rem">
        Excluded · {{ listing._exclusions.join(' · ') }}
      </div>

      <div v-if="listing._score !== null" class="score-section">
        <div class="score-title" :style="{ color: scoreColor(listing._score) }">
          Score {{ Math.round(listing._score) }} / 100
        </div>
        <div v-for="comp in SCORE_COMPONENTS" :key="comp.key">
          <div class="score-row">
            <span>{{ comp.label }}</span>
            <span class="score-val">{{ componentPercent(comp) }}%</span>
          </div>
          <div class="progress-bar-wrap">
            <div class="progress-bar-fill" :style="{ width: Math.min(100, ((listing._components?.[comp.key] || 0) / componentMax(comp)) * 100) + '%' }"></div>
          </div>
        </div>
      </div>

      <div v-if="listing._explanation" class="explanation-section">
        <div class="score-title">Why this property?</div>
        <p>{{ listing._explanation.summary }}</p>
      </div>
      <div v-if="listing._commute" class="commute-section">
        <div class="score-title">Commute</div>
        <div v-if="listing._commute.available">Average commute score: {{ listing._commute.score }}/100</div>
        <div v-for="destination in listing._commute.destinations" :key="destination.name" class="change-row">{{ destination.name }} <span>{{ destination.minutes }} min · {{ destination.distance_km }} km</span></div>
        <div v-if="!listing._commute.available" class="purchase-unavailable">{{ listing._commute.reason }}</div>
      </div>

      <div class="purchase-estimate">
        <div class="score-title">Purchase feasibility</div>
        <template v-if="listing._purchase_estimate?.available">
          <div class="purchase-grid">
            <span>Taxes</span><strong>€{{ listing._purchase_estimate.tax.toLocaleString('nl-BE') }}</strong>
            <span>Notary + mortgage</span><strong>€{{ (listing._purchase_estimate.notary + listing._purchase_estimate.mortgage_cost).toLocaleString('nl-BE') }}</strong>
            <span>Estimated loan</span><strong>€{{ listing._purchase_estimate.estimated_loan.toLocaleString('nl-BE') }}</strong>
            <span>Own cash needed</span><strong>€{{ listing._purchase_estimate.required_cash.toLocaleString('nl-BE') }}</strong>
          </div>
          <div :class="['purchase-balance', { shortfall: listing._purchase_estimate.cash_surplus < 0 }]">
            {{ listing._purchase_estimate.cash_surplus >= 0 ? 'Cash remaining' : 'Cash shortfall' }}:
            €{{ Math.abs(listing._purchase_estimate.cash_surplus).toLocaleString('nl-BE') }}
          </div>
        </template>
        <div v-else class="purchase-unavailable">Estimate unavailable: {{ (listing._purchase_estimate?.missing || ['finance settings']).join(', ') }}</div>
      </div>

      <div class="workflow-section">
        <div class="score-title">Contact pipeline</div>
        <div class="detail-rating" @mouseleave="detailHoverRating = 0">
          <button v-for="n in 5" :key="n" :class="['rating-star', 'rating-star-lg', { filled: n <= (detailHoverRating || workflow.rating || 0) }]" @mouseenter="detailHoverRating = n" @click="workflow.rating = workflow.rating === n ? null : n" :title="`${n} star${n > 1 ? 's' : ''}`">★</button>
        </div>
        <div class="workflow-grid">
          <label>Status<select v-model="workflow.status"><option>New</option><option>Interested</option><option>Contacted</option><option>Visit planned</option><option>Offer</option><option>On hold</option><option>Rejected</option></select></label>
          <label>Contact date<input v-model="workflow.contact_date" type="date" /></label>
          <label>Follow-up<input v-model="workflow.next_follow_up_date" type="date" /></label>
          <label>Agent<input v-model="workflow.agent_name" type="text" placeholder="Name" /></label>
          <label>Phone<input v-model="workflow.agent_phone" type="tel" /></label>
          <label>Email<input v-model="workflow.agent_email" type="email" /></label>
        </div>
        <button class="btn btn-primary btn-sm" :disabled="workflowSaving" @click="saveWorkflow">{{ workflowSaving ? 'Saving…' : 'Save pipeline' }}</button>
      </div>

      <div class="property-note-section">
        <div class="score-title">Notes <span v-if="noteSaved" class="note-saved-badge">Saved</span></div>
        <textarea class="property-note-input" v-model="note" rows="3" placeholder="Add a note about this property…" @input="scheduleNoteSave"></textarea>
      </div>

      <div class="interaction-section">
        <div class="score-title">Log contact</div>
        <div class="interaction-form">
          <label>Type<select v-model="interactionKind" class="interaction-kind"><option value="call">Call</option><option value="email">Email</option><option value="message">Message</option><option value="visit">Visit</option><option value="other">Other</option></select></label>
          <label>Note<textarea v-model="interactionNote" class="interaction-note" rows="2" placeholder="What happened?" @keyup.ctrl.enter="logInteraction"></textarea></label>
          <label>Next follow-up<input v-model="interactionFollowUp" class="interaction-follow-up" type="date" /></label>
        </div>
        <button class="btn btn-primary btn-sm log-interaction" :disabled="interactionSaving || !interactionNote.trim()" @click="logInteraction">{{ interactionSaving ? 'Saving…' : 'Log interaction' }}</button>
        <div v-if="interactionError" class="interaction-error" aria-live="polite">{{ interactionError }}</div>
        <div v-if="interactions.length" class="interaction-timeline">
          <article v-for="interaction in interactions" :key="interaction.id" class="interaction-item">
            <div class="interaction-meta"><strong>{{ interactionLabel(interaction.kind) }}</strong><span>{{ interactionDate(interaction.occurred_at) }}</span></div>
            <p v-if="interaction.note">{{ interaction.note }}</p>
            <small v-if="interaction.next_follow_up_date">Follow-up: {{ interaction.next_follow_up_date }}</small>
          </article>
        </div>
      </div>

      <div v-if="changes.length" class="changes-section">
        <div class="score-title">Recent changes</div>
        <div v-for="change in changes.slice(-8).reverse()" :key="change.observed_at + change.field" class="change-row">
          <span>{{ change.field === 'price' ? 'Price' : change.field === 'photos' ? 'Photos' : change.field }}</span>
          <strong :class="{ 'change-positive': change.change_type === 'price_reduction' }">{{ change.change_type === 'price_reduction' ? 'Price reduced' : change.change_type === 'photos_added' ? 'Photos added' : `${change.old_value || 'Unknown'} → ${change.new_value || 'Unknown'}` }}</strong>
        </div>
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
      <div v-else class="detail-no-photos">No photos available</div>

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

    <div v-if="modalOpen" class="image-modal" role="dialog" aria-modal="true" @click.self="modalOpen = false">
      <button class="image-modal-close" type="button" aria-label="Close image" @click="modalOpen = false">×</button>
      <img :src="images[imageIdx]" :alt="listing.source" />
    </div>
  </div>
</template>
