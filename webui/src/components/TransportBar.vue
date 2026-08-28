<script setup lang="ts">
import { computed } from 'vue'
import type { Phase, SourceKind } from '../types'
import { fmtClock } from '../utils/time'

const props = defineProps<{
  phase: Phase
  kind: SourceKind
  playing: boolean
  rate: number
  position: number
  duration: number
  hasAudio: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'stop'): void
  (e: 'rate', r: number): void
}>()

const RATES = [0.5, 1, 1.5, 2, 4]

const enabled = computed(
  () => props.hasAudio && props.kind !== 'mic' && (props.phase === 'processing' || props.phase === 'done'),
)
const pct = computed(() =>
  props.duration > 0 ? Math.min(100, (props.position / props.duration) * 100) : 0,
)
const rateLabel = (r: number) => (r === 4 ? '最快' : `${r}×`)
</script>

<template>
  <div class="transport" :class="{ off: !enabled }">
    <button
      class="t-btn play"
      :disabled="!enabled"
      :title="playing ? '暂停' : '播放'"
      @click="emit('toggle')"
    >
      <svg v-if="playing" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <rect x="3.4" y="2.6" width="3.4" height="10.8" rx="1.2" fill="currentColor" />
        <rect x="9.2" y="2.6" width="3.4" height="10.8" rx="1.2" fill="currentColor" />
      </svg>
      <svg v-else viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M4.6 2.4 L13.4 8 L4.6 13.6 Z" fill="currentColor" />
      </svg>
    </button>
    <button class="t-btn" :disabled="!enabled || phase === 'processing'" title="回到开头" @click="emit('stop')">
      <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
        <path d="M3 2.5 v11 h2 v-11 Z M13 13.5 L5.5 8 L13 2.5 Z" fill="currentColor" />
      </svg>
    </button>

    <div class="rates" role="group" aria-label="倍速">
      <button
        v-for="r in RATES"
        :key="r"
        class="rate"
        :class="{ on: rate === r }"
        :disabled="!enabled"
        @click="emit('rate', r)"
      >
        {{ rateLabel(r) }}
      </button>
    </div>

    <div class="time mono">
      <span class="cur">{{ fmtClock(position) }}</span>
      <span class="sep">/</span>
      <span class="total">{{ fmtClock(duration) }}</span>
      <span class="bar">
        <i :style="{ width: pct + '%' }" />
      </span>
    </div>
  </div>
</template>

<style scoped>
.transport {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: var(--bg-1);
  border: 1px solid var(--line-1);
  border-radius: var(--radius);
  transition: opacity 0.2s var(--ease);
}
.transport.off {
  opacity: 0.55;
}
.t-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
  color: var(--ink-hi);
  transition: all 0.15s var(--ease);
}
.t-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.t-btn:disabled {
  opacity: 0.35;
}
.t-btn.play {
  color: var(--accent);
  border-color: var(--accent);
}
.rates {
  display: flex;
  gap: 3px;
  padding: 2px;
  border-radius: 99px;
  background: var(--bg-2);
  border: 1px solid var(--line-1);
}
.rate {
  height: 22px;
  padding: 0 9px;
  border-radius: 99px;
  font-size: 11.5px;
  color: var(--ink-mid);
  transition: all 0.15s var(--ease);
}
.rate:hover:not(:disabled) {
  color: var(--ink-hi);
}
.rate.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.rate:disabled {
  opacity: 0.4;
}
.time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  margin-left: auto;
}
.cur {
  color: var(--ink-hi);
}
.sep,
.total {
  color: var(--ink-low);
}
.bar {
  width: 90px;
  height: 4px;
  border-radius: 99px;
  background: var(--bg-3);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: var(--accent);
  transition: width 0.12s linear;
}
</style>
