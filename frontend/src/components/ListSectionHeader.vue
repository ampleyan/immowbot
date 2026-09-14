<script setup lang="ts">
defineProps<{
  name: string
  count: number
  open: boolean
  controlsId: string
}>()

const emit = defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    type="button"
    class="list-header"
    :aria-expanded="open"
    :aria-controls="controlsId"
    @click="emit('toggle')"
  >
    <span class="list-name">{{ name }}</span>
    <span class="list-count">{{ count }} {{ count === 1 ? 'property' : 'properties' }}</span>
    <span :class="['list-chevron', { open }]" aria-hidden="true">▼</span>
  </button>
</template>
