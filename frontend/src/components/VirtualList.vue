<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(defineProps<{
  items: unknown[]
  itemHeight?: number
  maxHeight?: number
}>(), {
  itemHeight: 96,
  maxHeight: 560,
})

const scrollTop = ref(0)

const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - 1))
const endIndex = computed(() => Math.min(
  props.items.length,
  startIndex.value + Math.ceil(props.maxHeight / props.itemHeight) + 2,
))
const visibleItems = computed(() => props.items.slice(startIndex.value, endIndex.value))
const totalHeight = computed(() => props.items.length * props.itemHeight)

function handleScroll(event: Event) {
  scrollTop.value = (event.target as HTMLElement).scrollTop
}
</script>

<template>
  <div
    class="virtual-list"
    :style="{ maxHeight: `${props.maxHeight}px` }"
    @scroll="handleScroll"
  >
    <div class="virtual-list-spacer" :style="{ height: `${totalHeight}px` }">
      <div
        class="virtual-list-window"
        :style="{ transform: `translateY(${startIndex * props.itemHeight}px)` }"
      >
        <div
          v-for="(item, offset) in visibleItems"
          :key="startIndex + offset"
          class="virtual-list-item"
          :style="{ height: `${props.itemHeight}px` }"
        >
          <slot :item="item" :index="startIndex + offset" />
        </div>
      </div>
    </div>
  </div>
</template>
