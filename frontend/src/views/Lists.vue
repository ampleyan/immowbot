<script setup>
import { computed, ref, onMounted } from 'vue'
import { api } from '../api.js'
import ListPropertyRow from '../components/ListPropertyRow.vue'
import ListSectionHeader from '../components/ListSectionHeader.vue'
import VirtualList from '../components/VirtualList.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const lists = ref([])
const smartLists = ref([])
const expanded = ref(new Set())
const listItems = ref({})
const newName = ref('')
const loading = ref(true)
const sectionKeys = computed(() => [
  ...smartLists.value.map(lst => 'smart-' + lst.id),
  ...lists.value.map(lst => lst.id),
])
const allExpanded = computed(() => sectionKeys.value.length > 0 && sectionKeys.value.every(key => expanded.value.has(key)))

async function load() {
  try { lists.value = await api.getLists() } catch {}
  try { smartLists.value = await api.getSmartLists() } catch { smartLists.value = [] }
  loading.value = false
}

onMounted(load)

async function toggle(listId) {
  const s = new Set(expanded.value)
  if (s.has(listId)) {
    s.delete(listId)
  } else {
    s.add(listId)
    await loadItems(listId)
  }
  expanded.value = s
}

async function loadItems(listId) {
  try { listItems.value[listId] = await api.getListItems(listId) } catch { listItems.value[listId] = [] }
}

async function loadSmartItems(listId) {
  try { listItems.value['smart-' + listId] = await api.getSmartListItems(listId) } catch { listItems.value['smart-' + listId] = [] }
}

async function toggleSmart(listId) {
  const key = 'smart-' + listId
  const s = new Set(expanded.value)
  if (s.has(key)) s.delete(key)
  else { s.add(key); await loadSmartItems(listId) }
  expanded.value = s
}

async function toggleAll() {
  if (allExpanded.value) {
    expanded.value = new Set()
    return
  }

  expanded.value = new Set(sectionKeys.value)
  await Promise.all(sectionKeys.value.map(key => {
    if (listItems.value[key]) return Promise.resolve()
    if (String(key).startsWith('smart-')) return loadSmartItems(String(key).slice(6))
    return loadItems(key)
  }))
}

async function createList() {
  if (!newName.value.trim()) return
  await api.createList(newName.value.trim())
  newName.value = ''
  await load()
}

async function deleteList(listId) {
  await api.deleteList(listId)
  const s = new Set(expanded.value)
  s.delete(listId)
  expanded.value = s
  await load()
}

async function removeItem(listId, source, sid) {
  await api.removeFromList(listId, source, String(sid))
  await loadItems(listId)
  await load()
}

function openListing(item) {
  if (item.url) window.open(item.url, '_blank', 'noopener')
}

</script>

<template>
  <div>
    <LoadingSpinner v-if="loading" label="Loading lists" />
    <template v-else>
    <div v-if="sectionKeys.length" class="list-controls">
      <span>{{ sectionKeys.length }} {{ sectionKeys.length === 1 ? 'list' : 'lists' }}</span>
      <button type="button" class="btn btn-ghost btn-sm" @click="toggleAll">
        {{ allExpanded ? 'Collapse all' : 'Expand all' }}
      </button>
    </div>
    <div v-if="smartLists.length" class="smart-lists-section">
      <h3>Smart lists</h3>
      <div v-for="lst in smartLists" :key="lst.id" class="list-item smart-list-item">
        <ListSectionHeader :name="lst.name" :count="lst.item_count" :open="expanded.has('smart-' + lst.id)" :controls-id="'smart-list-' + lst.id" @toggle="toggleSmart(lst.id)" />
        <div v-if="expanded.has('smart-' + lst.id)" :id="'smart-list-' + lst.id" class="list-body">
          <div v-if="!listItems['smart-' + lst.id]" style="padding:0.75rem 1rem;font-size:0.8rem;color:#98A2B3">Loading…</div>
          <div v-else-if="!listItems['smart-' + lst.id].length" class="empty" style="padding:0.75rem 0">No matching properties.</div>
          <VirtualList v-else :items="listItems['smart-' + lst.id]" class="grouped-cards">
            <template #default="{ item }">
              <ListPropertyRow :listing="item" @open="openListing(item)" />
            </template>
          </VirtualList>
        </div>
      </div>
    </div>
    <div class="create-list-row">
      <input v-model="newName" type="text" placeholder="New list name…" @keyup.enter="createList" />
      <button class="btn btn-primary" @click="createList">Create</button>
    </div>

    <div v-if="!lists.length" class="empty">No lists yet. Use 📋 Lists on any property to save it.</div>

    <div v-for="lst in lists" :key="lst.id" class="list-item">
      <ListSectionHeader :name="lst.name" :count="lst.item_count" :open="expanded.has(lst.id)" :controls-id="'list-' + lst.id" @toggle="toggle(lst.id)" />

      <div v-if="expanded.has(lst.id)" :id="'list-' + lst.id" class="list-body">
        <div v-if="!listItems[lst.id]" style="padding:0.75rem 1rem;font-size:0.8rem;color:#98A2B3">Loading…</div>
        <div v-else-if="!listItems[lst.id].length" class="empty" style="padding:0.75rem 0">Empty list.</div>
        <template v-else>
          <VirtualList :items="listItems[lst.id]" class="grouped-cards">
            <template #default="{ item }">
              <ListPropertyRow :listing="{ ...item, _score: item._score ?? null }" removable @open="openListing(item)" @remove="removeItem(lst.id, item.source, item.source_listing_id)" />
            </template>
          </VirtualList>
        </template>

        <div class="list-footer">
          <button class="btn btn-ghost btn-sm" style="color:#C01048" @click="deleteList(lst.id)">Delete list</button>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>
