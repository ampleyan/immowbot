<script setup>
import { computed } from 'vue'

const props = defineProps({
  state: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['cancel'])

const phaseLabel = computed(() => ({
  starting: 'Preparing collection',
  scraping: 'Scraping listings',
  translation: 'Translating descriptions',
  completed: 'Collection complete',
  cancelled: 'Collection cancelled',
  error: 'Collection failed',
  idle: 'Ready',
}[props.state.phase] || 'Collection in progress'))

const phaseIcon = computed(() => ({ starting: '·', scraping: '↗', translation: 'T', completed: '✓', cancelled: '—', idle: '·' }[props.state.phase] || '↗'))
const isTerminal = computed(() => ['completed', 'cancelled', 'error'].includes(props.state.phase) || (!props.state.alive && props.state.status))
const progressWidth = computed(() => {
  if (props.state.phase === 'translation') {
    return props.state.translation_total ? Math.round((props.state.translation_done / props.state.translation_total) * 100) : 0
  }
  if (props.state.portal_total) return Math.round((props.state.portal_index / props.state.portal_total) * 100)
  return 0
})
const progressLabel = computed(() => {
  if (props.state.phase === 'translation') return `${props.state.translation_done || 0} of ${props.state.translation_total || 0}`
  if (props.state.portal_total) return `Portal ${props.state.portal_index || 1} of ${props.state.portal_total}`
  return 'Starting'
})
const currentLabel = computed(() => props.state.phase === 'translation'
  ? props.state.translation_current_address || props.state.translation_current
  : props.state.current_address || props.state.current_id)

function elapsedLabel(seconds) {
  const total = Math.max(0, Number(seconds || 0))
  const minutes = Math.floor(total / 60)
  const secs = String(total % 60).padStart(2, '0')
  return minutes ? `${minutes}m ${secs}s` : `${secs}s`
}
</script>

<template>
  <section v-if="state.alive || isTerminal" :class="['scrape-progress', { compact, terminal: isTerminal, error: state.status === 'error' }]" role="status" aria-live="polite">
    <div class="scrape-progress-head">
      <span class="scrape-progress-icon" aria-hidden="true">{{ phaseIcon }}</span>
      <div class="scrape-progress-heading">
        <strong>{{ phaseLabel }}</strong>
        <span v-if="state.portal">{{ state.portal }}</span>
      </div>
      <span class="scrape-progress-time">{{ elapsedLabel(state.elapsed_seconds) }}</span>
    </div>
    <div class="scrape-progress-track" aria-hidden="true">
      <div class="scrape-progress-fill" :class="{ indeterminate: !progressWidth && state.alive }" :style="{ width: `${progressWidth}%` }" />
    </div>
    <div class="scrape-progress-meta">
      <span>{{ progressLabel }}</span>
      <span>{{ state.checked || 0 }} checked</span>
      <span>{{ state.saved || 0 }} saved</span>
      <span v-if="state.failed">{{ state.failed }} failed</span>
    </div>
    <div v-if="currentLabel && state.alive" class="scrape-progress-current" :title="currentLabel">
      <span>Now</span> {{ currentLabel }}
    </div>
    <div v-if="state.error" class="scrape-progress-error">{{ state.error }}</div>
    <button v-if="state.alive" class="scrape-progress-cancel" type="button" @click="emit('cancel')">Stop collection</button>
  </section>
</template>

<style scoped>
.scrape-progress { display: grid; gap: 0.45rem; margin: 0 0 1rem; padding: 0.85rem 1rem; border: 1px solid #f0c4d8; border-radius: 10px; background: #fff8fb; color: #7a1745; box-shadow: 0 5px 18px rgba(122, 23, 69, 0.08); }
.scrape-progress.compact { margin: 0.55rem 0 0; padding: 0.65rem 0.7rem; border-color: rgba(245, 196, 0, 0.22); background: rgba(255,255,255,0.05); color: #f5c400; box-shadow: none; }
.scrape-progress-head { display: flex; align-items: center; gap: 0.55rem; min-width: 0; }
.scrape-progress-icon { display: grid; place-items: center; width: 1.25rem; height: 1.25rem; border-radius: 50%; background: #fce7f3; color: #b02a6f; font-size: 0.75rem; font-weight: 800; }
.compact .scrape-progress-icon { background: rgba(245,196,0,0.14); color: #f5c400; }
.scrape-progress-heading { display: grid; gap: 0.08rem; min-width: 0; font-size: 0.78rem; }
.scrape-progress-heading span, .scrape-progress-time, .scrape-progress-meta, .scrape-progress-current { color: #667085; font-size: 0.68rem; }
.compact .scrape-progress-heading span, .compact .scrape-progress-time, .compact .scrape-progress-meta, .compact .scrape-progress-current { color: rgba(255,255,255,0.58); }
.scrape-progress-time { margin-left: auto; white-space: nowrap; }
.scrape-progress-track { height: 0.35rem; overflow: hidden; border-radius: 999px; background: #fce7f3; }
.compact .scrape-progress-track { background: rgba(255,255,255,0.12); }
.scrape-progress-fill { height: 100%; border-radius: inherit; background: #e83e8c; transition: width 0.35s ease; }
.scrape-progress-fill.indeterminate { width: 35% !important; animation: scrape-progress-slide 1.2s ease-in-out infinite; }
.scrape-progress-meta { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; }
.scrape-progress-current { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.scrape-progress-current span { color: #b02a6f; font-weight: 700; margin-right: 0.25rem; }
.compact .scrape-progress-current span { color: #f5c400; }
.scrape-progress-cancel { justify-self: start; border: 0; padding: 0; background: transparent; color: #b02a6f; cursor: pointer; font: inherit; font-size: 0.68rem; font-weight: 700; }
.compact .scrape-progress-cancel { color: #f5c400; }
.scrape-progress-error { color: #b42318; font-size: 0.7rem; }
.scrape-progress.terminal { box-shadow: none; }
.scrape-progress.error { border-color: #fecdca; background: #fff5f4; }
@keyframes scrape-progress-slide { 0% { transform: translateX(-120%); } 100% { transform: translateX(310%); } }
@media (prefers-reduced-motion: reduce) { .scrape-progress-fill.indeterminate { animation: none; width: 100% !important; } }
</style>
