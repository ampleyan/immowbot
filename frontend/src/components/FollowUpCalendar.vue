<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  listings: Array<{ url?: string; postcode?: string; _workflow?: { next_follow_up_date?: string | null } }>
  month?: string
}>(), {
  month: () => new Date().toISOString().slice(0, 7),
})

const emit = defineEmits<{ select: [url: string] }>()

function dateKey(date: Date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-')
}

const monthLabel = computed(() => new Date(`${props.month}-01T12:00:00`).toLocaleDateString('en-BE', { month: 'long', year: 'numeric' }))
const days = computed(() => {
  const parts = props.month.split('-').map(Number)
  const year = parts[0] || new Date().getFullYear()
  const month = parts[1] || new Date().getMonth() + 1
  const first = new Date(year, month - 1, 1)
  const start = new Date(year, month - 1, 1 - first.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const key = dateKey(date)
    return { key, day: date.getDate(), inMonth: date.getMonth() === month - 1, items: props.listings.filter(listing => listing._workflow?.next_follow_up_date === key) }
  })
})
</script>

<template>
  <div class="follow-up-calendar">
    <div class="follow-up-calendar-title">{{ monthLabel }}</div>
    <div class="follow-up-calendar-weekdays"><span v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="day">{{ day }}</span></div>
    <div class="follow-up-calendar-grid">
      <div v-for="day in days" :key="day.key" :class="['follow-up-day', { muted: !day.inMonth, busy: day.items.length }]">
        <span>{{ day.day }}</span>
        <button v-for="item in day.items.slice(0, 3)" :key="item.url" type="button" @click="emit('select', item.url || '')">{{ item.postcode || 'Property' }}</button>
        <small v-if="day.items.length > 3">+{{ day.items.length - 3 }} more</small>
      </div>
    </div>
  </div>
</template>
