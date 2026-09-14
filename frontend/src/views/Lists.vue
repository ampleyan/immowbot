<script setup>
import { computed, ref, onMounted } from 'vue'
import { api } from '../api.js'
import PropertyCard from '../components/PropertyCard.vue'
import DetailPanel from '../components/DetailPanel.vue'
import SavePanel from '../components/SavePanel.vue'
import ListSectionHeader from '../components/ListSectionHeader.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const lists = ref([])
const smartLists = ref([])
const expanded = ref(new Set())
const listItems = ref({})
const newName = ref('')
const loading = ref(true)
const selectedUrl = ref(null)
const savingUrl = ref(null)

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

async function reloadExpanded() {
  await Promise.all([...expanded.value].map(key => {
    if (String(key).startsWith('smart-')) return loadSmartItems(String(key).slice(6))
    return loadItems(key)
  }))
}

async function onPanelUpdated() {
  await load()
  await reloadExpanded()
}

function toggleDetail(url) {
  selectedUrl.value = selectedUrl.value === url ? null : url
  savingUrl.value = null
}

function toggleSave(url) {
  savingUrl.value = savingUrl.value === url ? null : url
  selectedUrl.value = null
}

async function quickStatus(listing, status) {
  const rejectionReason = status === 'Rejected' ? window.prompt('Why are you rejecting this property?', listing._workflow?.rejection_reason || '') : ''
  if (status === 'Rejected' && rejectionReason === null) return
  try {
    await api.saveWorkflow(listing.source, listing.source_listing_id, { status, rejection_reason: rejectionReason || '' })
    await reloadExpanded()
  } catch {}
}

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
          <div v-else class="grouped-cards">
            <template v-for="item in listItems['smart-' + lst.id]" :key="item.source + ':' + item.source_listing_id">
              <PropertyCard
                :listing="item"
                :isSaving="savingUrl === item.url"
                :showSelect="false"
                @toggle-detail="toggleDetail(item.url)"
                @toggle-save="toggleSave(item.url)"
                @quick-status="quickStatus(item, $event)"
              />
              <SavePanel v-if="savingUrl === item.url" :listing="item" :allLists="lists" @updated="onPanelUpdated" />
              <DetailPanel v-if="selectedUrl === item.url" :listing="item" @updated="onPanelUpdated" />
            </template>
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
      <ListSectionHeader :name="lst.name" :count="lst.item_count" :open="expanded.has(lst.id)" :controls-id="'list-' + lst.id" @toggle="toggle(lst.id)" />

      <div v-if="expanded.has(lst.id)" :id="'list-' + lst.id" class="list-body">
        <div v-if="!listItems[lst.id]" style="padding:0.75rem 1rem;font-size:0.8rem;color:#98A2B3">Loading…</div>
        <div v-else-if="!listItems[lst.id].length" class="empty" style="padding:0.75rem 0">Empty list.</div>
        <template v-else>
          <div class="grouped-cards">
            <template v-for="item in listItems[lst.id]" :key="item.source + ':' + item.source_listing_id">
              <PropertyCard
                :listing="item"
                :isSaving="savingUrl === item.url"
                :showSelect="false"
                @toggle-detail="toggleDetail(item.url)"
                @toggle-save="toggleSave(item.url)"
                @quick-status="quickStatus(item, $event)"
              />
              <SavePanel v-if="savingUrl === item.url" :listing="item" :allLists="lists" @updated="onPanelUpdated" />
              <DetailPanel v-if="selectedUrl === item.url" :listing="item" @updated="onPanelUpdated" />
            </template>
          </div>
        </template>

        <div class="list-footer">
          <button class="btn btn-ghost btn-sm" style="color:#C01048" @click="deleteList(lst.id)">Delete list</button>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>
