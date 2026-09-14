<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import ListPropertyRow from '../components/ListPropertyRow.vue'

const lists = ref([])
const smartLists = ref([])
const duplicates = ref([])
const expanded = ref(new Set())
const listItems = ref({})
const newName = ref('')

async function load() {
  try { lists.value = await api.getLists() } catch {}
  try { smartLists.value = await api.getSmartLists() } catch { smartLists.value = [] }
  try { duplicates.value = await api.getDuplicates() } catch { duplicates.value = [] }
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

function fmtPrice(price) {
  if (!price) return '—'
  return '€' + Math.round(price).toLocaleString('nl-BE')
}

</script>

<template>
  <div>
    <div v-if="duplicates.length" class="smart-lists-section">
      <h3>Possible duplicates</h3>
      <div v-for="group in duplicates" :key="group.canonical.url" class="duplicate-group">
        <div><strong>{{ group.confidence }} confidence</strong> · {{ group.offers.length }} portal offers</div>
        <div v-for="offer in group.offers" :key="offer.source + offer.source_listing_id" class="duplicate-offer"><span>{{ offer.source }} · {{ fmtPrice(offer.price) }}</span><a :href="offer.url" target="_blank">Open ↗</a></div>
        <small>Signals: {{ group.signals.map(s => s.source + ' (' + s.signals.join(', ') + ')').join('; ') }}</small>
      </div>
    </div>
    <div v-if="smartLists.length" class="smart-lists-section">
      <h3>Smart lists</h3>
      <div v-for="lst in smartLists" :key="lst.id" class="list-item smart-list-item">
        <div class="list-header" @click="toggleSmart(lst.id)">
          <span class="list-name">{{ lst.name }}</span>
          <span class="list-count">{{ lst.item_count }} {{ lst.item_count === 1 ? 'property' : 'properties' }}</span>
          <span :class="['list-chevron', { open: expanded.has('smart-' + lst.id) }]">▼</span>
        </div>
        <div v-if="expanded.has('smart-' + lst.id)" class="list-body">
          <div v-if="!listItems['smart-' + lst.id]" style="padding:0.75rem 1rem;font-size:0.8rem;color:#98A2B3">Loading…</div>
          <div v-else-if="!listItems['smart-' + lst.id].length" class="empty" style="padding:0.75rem 0">No matching properties.</div>
          <div v-else class="grouped-cards">
            <div v-for="item in listItems['smart-' + lst.id]" :key="item.source + item.source_listing_id">
              <ListPropertyRow :listing="item" @open="openListing(item)" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="create-list-row">
      <input v-model="newName" type="text" placeholder="New list name…" @keyup.enter="createList" />
      <button class="btn btn-primary" @click="createList">Create</button>
    </div>

    <div v-if="!lists.length" class="empty">No lists yet. Use 📋 Lists on any property to save it.</div>

    <div v-for="lst in lists" :key="lst.id" class="list-item">
      <div class="list-header" @click="toggle(lst.id)">
        <span class="list-name">{{ lst.name }}</span>
        <span class="list-count">{{ lst.item_count }} {{ lst.item_count === 1 ? 'property' : 'properties' }}</span>
        <span :class="['list-chevron', { open: expanded.has(lst.id) }]">▼</span>
      </div>

      <div v-if="expanded.has(lst.id)" class="list-body">
        <div v-if="!listItems[lst.id]" style="padding:0.75rem 1rem;font-size:0.8rem;color:#98A2B3">Loading…</div>
        <div v-else-if="!listItems[lst.id].length" class="empty" style="padding:0.75rem 0">Empty list.</div>
        <template v-else>
          <div class="grouped-cards">
            <div v-for="item in listItems[lst.id]" :key="item.source + item.source_listing_id">
              <ListPropertyRow :listing="{ ...item, _score: item._score ?? null }" removable @open="openListing(item)" @remove="removeItem(lst.id, item.source, item.source_listing_id)" />
            </div>
          </div>
        </template>

        <div class="list-footer">
          <button class="btn btn-ghost btn-sm" style="color:#C01048" @click="deleteList(lst.id)">Delete list</button>
        </div>
      </div>
    </div>
  </div>
</template>
