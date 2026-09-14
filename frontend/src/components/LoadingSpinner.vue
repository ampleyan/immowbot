<script setup>
defineProps({ label: { type: String, default: 'Loading' } })
</script>

<template>
  <div class="loading-state" role="status" :aria-label="label">
    <span class="loading-spinner" aria-hidden="true"></span>
    <span>{{ label }}…</span>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  min-height: 8rem;
  color: #667085;
  font-size: 0.82rem;
}

.loading-spinner {
  width: 1.15rem;
  height: 1.15rem;
  border: 2px solid #F0C4D8;
  border-top-color: #E83E8C;
  border-radius: 50%;
  animation: loading-spin 0.75s linear infinite;
}

@keyframes loading-spin {
  to { transform: rotate(360deg); }
}
</style>
