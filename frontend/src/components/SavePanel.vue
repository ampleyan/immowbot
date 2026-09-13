<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../api.js'

const props = defineProps(['listing', 'allLists'])
const emit = defineEmits(['updated'])

const CREATE_OPT = '＋ New list…'

const inListIds = ref(new Set(props.listing._list_ids || []))
const note = ref(props.listing._note || '')
const selectedList = ref('')
const newListName = ref('')
const creating = computed(() => selectedList.value === CREATE_OPT)

watch(() => props.listing, (l) => {
  inListIds.value = new Set(l._list_ids || [])
  note.value = l._note || ''
  selectedList.value = ''
  newListName.value = ''
})

const availableLists = computed(() =>
  (props.allLists || []).filter(l => !inListIds.value.has(l.id))
)
const inLists = computed(() =>
  (props.allLists || []).filter(l => inListIds.value.has(l.id))
)
const selectOpts = computed(() => [...availableLists.value.map(l => l.name), CREATE_OPT])

const src = computed(() => props.listing.source || '')
const lid = computed(() => String(props.listing.source_listing_id || ''))

async function addToList() {
  if (creating.value) {
    if (!newListName.value.trim()) return
    const created = await api.createList(newListName.value.trim())
    await api.addToList(created.id, src.value, lid.value)
    inListIds.value = new Set([...inListIds.value, created.id])
    newListName.value = ''
    selectedList.value = ''
  } else {
    const lst = (props.allLists || []).find(l => l.name === selectedList.value)
    if (!lst) return
    await api.addToList(lst.id, src.value, lid.value)
    inListIds.value = new Set([...inListIds.value, lst.id])
    selectedList.value = ''
  }
  emit('updated')
}

async function removeFromList(listId) {
  await api.removeFromList(listId, src.value, lid.value)
  const s = new Set(inListIds.value)
  s.delete(listId)
  inListIds.value = s
  emit('updated')
}

async function saveNote() {
  await api.saveNote(src.value, lid.value, note.value)
  emit('updated')
}
</script>

<template>
  <div class="save-panel">
    <div class="save-panel-row">
      <select v-model="selectedList">
        <option value="" disabled>Add to list…</option>
        <option v-for="opt in selectOpts" :key="opt" :value="opt">{{ opt }}</option>
      </select>
      <template v-if="creating">
        <input v-model="newListName" type="text" placeholder="List name…" @keyup.enter="addToList" style="flex:1" />
        <button class="btn btn-primary btn-sm" @click="addToList">Create</button>
      </template>
      <button v-else class="btn btn-primary btn-sm" :disabled="!selectedList" @click="addToList">Add</button>
    </div>

    <div v-if="inLists.length" class="save-panel-badges">
      <span v-for="lst in inLists" :key="lst.id" class="pill pill-blue">
        {{ lst.name }}
        <span class="list-badge-remove" @click="removeFromList(lst.id)">✕</span>
      </span>
    </div>

    <hr class="save-panel-divider" />

    <textarea v-model="note" rows="3" placeholder="Notes about this property…"></textarea>
    <button class="btn btn-primary btn-sm" @click="saveNote">Save note</button>
  </div>
</template>
