<script setup lang="ts">
defineProps({
  open: { type: Boolean, default: false },
  mapped: { type: Number, default: 0 },
  withoutCoordinates: { type: Number, default: 0 },
})

const emit = defineEmits(['toggle'])
</script>

<template>
  <button type="button" class="map-section-header" :aria-expanded="open" aria-controls="listing-map-panel" @click="emit('toggle')">
    <span class="map-section-title">Map view</span>
    <span class="map-section-summary">{{ mapped }} mapped · {{ withoutCoordinates }} without coordinates</span>
    <span class="map-section-chevron" aria-hidden="true">{{ open ? '▲' : '▼' }}</span>
  </button>
</template>
