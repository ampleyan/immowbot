<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Select options' },
})
const emit = defineEmits(['update:modelValue'])
const open = ref(false)
const root = ref(null)

function toggleOption(option) {
  const values = props.modelValue.includes(option)
    ? props.modelValue.filter(value => value !== option)
    : [...props.modelValue, option]
  emit('update:modelValue', values)
}

function removeOption(option) {
  emit('update:modelValue', props.modelValue.filter(value => value !== option))
}

function closeOnOutside(event) {
  if (!root.value?.contains(event.target)) open.value = false
}

function closeOnEscape(event) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', closeOnOutside)
  document.addEventListener('keydown', closeOnEscape)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', closeOnOutside)
  document.removeEventListener('keydown', closeOnEscape)
})
</script>

<template>
  <div ref="root" class="chip-select" :class="{ open }">
    <div class="chip-select-input" role="combobox" :aria-expanded="open" aria-haspopup="listbox" tabindex="0" @click="open = !open" @keydown.enter.prevent="open = !open" @keydown.space.prevent="open = !open">
      <div class="chip-select-chips">
        <button v-for="value in modelValue" :key="value" class="filter-chip" type="button" @click.stop="removeOption(value)">{{ value }} <span aria-hidden="true">×</span></button>
        <span v-if="!modelValue.length" class="filter-placeholder">{{ placeholder }}</span>
      </div>
      <span class="chip-select-arrow" aria-hidden="true">⌄</span>
    </div>
    <div v-if="open" class="chip-select-menu" role="listbox" aria-multiselectable="true">
      <button v-for="option in options" :key="option" type="button" role="option" :aria-selected="modelValue.includes(option)" :class="['chip-select-option', { selected: modelValue.includes(option) }]" @click="toggleOption(option)">
        <span class="chip-select-check" aria-hidden="true">{{ modelValue.includes(option) ? '✓' : '' }}</span>{{ option }}
      </button>
      <div v-if="!options.length" class="chip-select-empty">No options available</div>
    </div>
  </div>
</template>
