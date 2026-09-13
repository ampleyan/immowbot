<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const lists = ref([])
const expanded = ref(new Set())
const listItems = ref({})
const newName = ref('')
const allNotes = ref({})

async function load() {
  try { lists.value = await api.getLists() } catch {}
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

function getImage(item) {
  const d = item.all_property_details || {}
  const candidates = [
    item.image_url_1, item.image_url_2,
    d['Image 1 URL'], d['Image 2 URL'],
    ...(Array.isArray(item.images) ? item.images : []),
  ]
  return candidates.find(u => typeof u === 'string' && u.startsWith('http')) || null
}

function fmtPrice(p) {
  if (!p) return '—'
  return '€' + Math.round(p).toLocaleString('nl-BE')
}

function specs(item) {
  const parts = []
  if (item.bedrooms) parts.push(`${Math.round(item.bedrooms)} bd`)
  if (item.surface_area) parts.push(`${Math.round(item.surface_area)} m²`)
  if (item.postcode) parts.push(item.postcode)
  return parts.join(' · ') || '—'
}
</script>

<template>
  <div>
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
          <div v-for="item in listItems[lst.id]" :key="item.source_listing_id" class="list-property">
            <div>
              <img v-if="getImage(item)" :src="getImage(item)" :alt="item.source" loading="lazy" />
              <div v-else class="list-property-placeholder">🏠</div>
            </div>
            <div class="list-property-data">
              <div class="list-property-price">{{ fmtPrice(item.price) }}
                <span style="font-size:0.78rem;font-weight:400;color:#667085;margin-left:0.3rem">
                  {{ (item.property_type || '').replace(/^\w/, c => c.toUpperCase()) }}
                </span>
              </div>
              <div class="list-property-specs">{{ specs(item) }}</div>
              <div v-if="item._note" class="list-property-note">{{ item._note }}</div>
            </div>
            <div class="list-property-actions">
              <a :href="item.url" target="_blank" class="btn btn-secondary btn-sm">Open ↗</a>
              <button class="btn btn-ghost btn-sm" @click="removeItem(lst.id, item.source, item.source_listing_id)">Remove</button>
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
