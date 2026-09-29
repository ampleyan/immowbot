<script setup>
import { ref, watch } from 'vue'
import Duplicates from './Duplicates.vue'
import Settings from './Settings.vue'

const props = defineProps({
  collectionState: { type: Object, required: true },
  isAdmin: { type: Boolean, default: false },
  initialSection: { type: String, default: 'tools' },
})

const section = ref(props.initialSection === 'settings' && props.isAdmin ? 'settings' : 'tools')

watch(() => [props.initialSection, props.isAdmin], ([initialSection, isAdmin]) => {
  section.value = initialSection === 'settings' && isAdmin ? 'settings' : 'tools'
})
</script>

<template>
  <div class="manage-view">
    <div class="manage-tabs status-panel" role="tablist" aria-label="Manage sections">
      <button
        class="status-option"
        :class="{ active: section === 'tools' }"
        type="button"
        role="tab"
        :aria-selected="section === 'tools'"
        @click="section = 'tools'"
      >Duplicates</button>
      <button
        v-if="isAdmin"
        class="status-option"
        :class="{ active: section === 'settings' }"
        type="button"
        role="tab"
        :aria-selected="section === 'settings'"
        @click="section = 'settings'"
      >Settings</button>
    </div>
    <Duplicates v-if="section === 'tools'" :collection-state="collectionState" />
    <Settings v-else-if="isAdmin" />
  </div>
</template>
