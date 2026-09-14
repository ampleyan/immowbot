<script setup>
import { computed, ref } from 'vue'
import { api } from '../api.js'

const props = defineProps({
  listing: { type: Object, required: true },
  allLists: { type: Array, default: () => [] },
})
const emit = defineEmits(['updated'])

const newListName = ref('')
const selectedList = ref('')
const note = ref(props.listing._note || '')
const status = ref(props.listing._workflow?.status || 'New')
const saving = ref('')
const CREATE_OPT = 'new'

const listIds = computed(() => new Set((props.listing._list_ids || []).map(id => String(id))))
const availableLists = computed(() => props.allLists.filter(list => !listIds.value.has(String(list.id))))

async function addToList() {
  if (selectedList.value === CREATE_OPT) {
    if (!newListName.value.trim()) return
    saving.value = 'list'
    try {
      const created = await api.createList(newListName.value.trim())
      await api.addToList(created.id, props.listing.source, String(props.listing.source_listing_id))
      selectedList.value = ''
      newListName.value = ''
      emit('updated')
    } finally {
      saving.value = ''
    }
    return
  }
  const list = availableLists.value.find(item => String(item.id) === selectedList.value)
  if (!list) return
  saving.value = 'list'
  try {
    await api.addToList(list.id, props.listing.source, String(props.listing.source_listing_id))
    selectedList.value = ''
    emit('updated')
  } finally {
    saving.value = ''
  }
}

async function saveNote() {
  saving.value = 'note'
  try {
    await api.saveNote(props.listing.source, String(props.listing.source_listing_id), note.value)
    emit('updated')
  } finally {
    saving.value = ''
  }
}

async function savePipeline() {
  saving.value = 'pipeline'
  try {
    await api.saveWorkflow(props.listing.source, String(props.listing.source_listing_id), { ...(props.listing._workflow || {}), status: status.value })
    emit('updated')
  } finally {
    saving.value = ''
  }
}
</script>

<template>
  <div class="comparison-actions">
    <div class="comparison-action-row">
      <select v-model="selectedList" class="list-select" aria-label="Add property to list">
        <option value="" disabled>Add to list…</option>
        <option v-for="list in availableLists" :key="list.id" :value="String(list.id)">{{ list.name }}</option>
        <option :value="CREATE_OPT">＋ New list…</option>
      </select>
      <input v-if="selectedList === CREATE_OPT" v-model="newListName" type="text" placeholder="List name…" aria-label="New list name" />
      <button type="button" class="btn btn-secondary btn-sm add-list" :disabled="!selectedList || saving === 'list'" @click="addToList">{{ saving === 'list' ? 'Saving…' : 'Add' }}</button>
    </div>
    <div class="comparison-action-row">
      <textarea v-model="note" rows="2" placeholder="Notes about this property…" aria-label="Property note"></textarea>
      <button type="button" class="btn btn-secondary btn-sm save-note" :disabled="saving === 'note'" @click="saveNote">{{ saving === 'note' ? 'Saving…' : 'Save note' }}</button>
    </div>
    <div class="comparison-action-row">
      <select v-model="status" class="pipeline-status" aria-label="Pipeline status">
        <option>New</option><option>Interested</option><option>Contacted</option><option>Visit planned</option><option>Offer</option><option>Rejected</option>
      </select>
      <button type="button" class="btn btn-primary btn-sm save-pipeline" :disabled="saving === 'pipeline'" @click="savePipeline">{{ saving === 'pipeline' ? 'Saving…' : 'Save pipeline' }}</button>
    </div>
  </div>
</template>
