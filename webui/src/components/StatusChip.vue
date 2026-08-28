<script setup lang="ts">
import { computed } from 'vue'
import type { Phase } from '../types'

const props = defineProps<{ phase: Phase }>()

const view = computed(() => {
  switch (props.phase) {
    case 'connecting':
      return { label: '连接中', cls: 'connecting' }
    case 'processing':
      return { label: '处理中', cls: 'processing' }
    case 'done':
      return { label: '完成', cls: 'done' }
    case 'error':
      return { label: '错误', cls: 'error' }
    default:
      return { label: '待机', cls: 'idle' }
  }
})
</script>

<template>
  <span class="chip" :class="view.cls" data-phase-chip>
    <span class="dot" />
    <span class="label">{{ view.label }}</span>
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 12px;
  border-radius: 99px;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
  font-size: 12px;
  color: var(--ink-mid);
  white-space: nowrap;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ink-low);
}
.connecting .dot {
  background: var(--accent);
  animation: pulse 1.1s ease-in-out infinite;
}
.processing .dot {
  background: var(--good);
  animation: pulse 1.1s ease-in-out infinite;
}
.done .dot {
  background: var(--good);
}
.error .dot {
  background: var(--bad);
}
.done .label {
  color: var(--good);
}
.error .label {
  color: var(--bad);
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(62, 207, 142, 0.5);
  }
  50% {
    opacity: 0.55;
    box-shadow: 0 0 0 5px rgba(62, 207, 142, 0);
  }
}
</style>
