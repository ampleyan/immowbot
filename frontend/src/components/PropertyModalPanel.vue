<script setup>
import { ref, watch } from 'vue'
import { api } from '../api.js'
import DetailPanel from './DetailPanel.vue'

const props = defineProps(['listing', 'showClose', 'inline'])
const emit = defineEmits(['updated', 'close'])

const noteOpen = ref(false)
const note = ref('')
const rejecting = ref(false)
const rating = ref(0)
const hoverRating = ref(0)
let noteSaveTimer = null

function initFromListing() {
  note.value = props.listing?._note || ''
  rating.value = props.listing?._workflow?.rating || 0
  rejecting.value = false
  noteOpen.value = false
  hoverRating.value = 0
}

initFromListing()
watch(() => props.listing?.url, initFromListing)

async function setRating(n) {
  rating.value = rating.value === n ? 0 : n
  try {
    await api.saveWorkflow(props.listing.source, String(props.listing.source_listing_id), { ...(props.listing._workflow || {}), rating: rating.value || null })
    emit('updated')
  } catch {}
}

async function setStatus(status) {
  try {
    await api.saveWorkflow(props.listing.source, String(props.listing.source_listing_id), { ...(props.listing._workflow || {}), status })
    emit('updated')
  } catch {}
}

function startReject() {
  noteOpen.value = true
  rejecting.value = true
}

async function confirmReject() {
  try {
    await Promise.all([
      api.saveWorkflow(props.listing.source, String(props.listing.source_listing_id), { ...(props.listing._workflow || {}), status: 'Rejected', rejection_reason: note.value || '' }),
      note.value ? api.saveNote(props.listing.source, props.listing.source_listing_id, note.value) : Promise.resolve(),
    ])
    emit('updated')
    emit('close')
  } catch {}
}

function scheduleNoteSave() {
  clearTimeout(noteSaveTimer)
  noteSaveTimer = setTimeout(async () => {
    if (!props.listing) return
    try { await api.saveNote(props.listing.source, props.listing.source_listing_id, note.value) } catch {}
  }, 800)
}

function fmtScrapedAt(iso) {
  if (!iso) return null
  const d = new Date(iso)
  const diffH = (Date.now() - d.getTime()) / 3600000
  if (diffH < 1) return 'scraped just now'
  if (diffH < 24) return `scraped ${Math.floor(diffH)}h ago`
  const diffD = Math.floor(diffH / 24)
  if (diffD === 1) return 'scraped yesterday'
  if (diffD < 7) return `scraped ${diffD}d ago`
  return `scraped ${d.toLocaleDateString('en-BE', { day: 'numeric', month: 'short' })}`
}
</script>

<template>
  <div :class="['modal-panel', { 'modal-panel-inline': inline }]">
    <div class="modal-actions-bar">
      <div class="modal-title-block">
        <div class="modal-title-price">€{{ listing.price?.toLocaleString('nl-BE') }}</div>
        <div class="modal-title-sub">
          {{ listing.postcode }} · {{ listing.source }}
          <span v-if="listing.source_listing_id"> · ID {{ listing.source_listing_id }}</span>
          <span v-if="fmtScrapedAt(listing._last_seen_at)"> · {{ fmtScrapedAt(listing._last_seen_at) }}</span>
        </div>
      </div>
      <div class="modal-action-btns">
        <button :class="['modal-note-btn', listing._workflow?.status === 'Interested' ? 'btn-interested' : 'btn-ghost']" title="Interested" @click="setStatus('Interested')">♥</button>
        <button class="modal-note-btn btn-ghost" title="On hold" @click="setStatus('On hold')">⏸</button>
        <button :class="['modal-note-btn', listing._workflow?.status === 'Rejected' || rejecting ? 'btn-red' : 'btn-ghost']" title="Reject" @click="startReject">✕</button>
        <button :class="['modal-note-btn', note ? 'btn-yellow' : 'btn-ghost']" title="Note" @click="noteOpen = !noteOpen; rejecting = noteOpen ? rejecting : false">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M2 2h12v9H9l-3 3v-3H2V2zm1 1v7h3v2l2-2h5V3H3z"/></svg>
        </button>
        <button v-if="showClose" class="modal-close" type="button" @click="emit('close')">×</button>
      </div>
      <div class="modal-rating" @mouseleave="hoverRating = 0">
        <button v-for="n in 5" :key="n" :class="['rating-star', 'rating-star-lg', { filled: n <= (hoverRating || rating) }]" @mouseenter="hoverRating = n" @click="setRating(n)" :title="`${n} star${n > 1 ? 's' : ''}`">★</button>
      </div>
    </div>
    <div v-if="noteOpen" class="modal-note-wrap">
      <textarea class="card-note-input" v-model="note" rows="2" :placeholder="rejecting ? 'Reason for rejection (optional)…' : 'Add a note about this property…'" @input="scheduleNoteSave" :autofocus="rejecting"></textarea>
      <div v-if="rejecting" class="modal-reject-confirm">
        <button class="btn btn-ghost btn-sm" @click="rejecting = false; noteOpen = false">Cancel</button>
        <button class="btn btn-sm modal-reject-confirm-btn" @click="confirmReject">Confirm rejection</button>
      </div>
    </div>
    <DetailPanel :listing="listing" @updated="emit('updated')" />
  </div>
</template>
