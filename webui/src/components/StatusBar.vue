<script setup lang="ts">
import { computed } from 'vue'
import { store, totalDur, avgConfidence, speakerStats } from '../store'
import { fmtTime, fmtDur } from '../types'

const speakerSummary = computed(() => {
  if (speakerStats.value.length === 0) return ''
  return speakerStats.value
    .map((sp) => `S${sp.speaker} ${fmtDur(sp.duration)}`)
    .join(' · ')
})

const phaseMeta = computed<{ label: string; cls: string }>(() => {
  switch (store.phase) {
    case 'idle':
      return { label: '就绪', cls: 'idle' }
    case 'connecting':
      return { label: '连接后端…', cls: 'connecting' }
    case 'ready':
      return { label: '管线就绪', cls: 'ready' }
    case 'streaming':
      return store.isTurbo
        ? { label: '处理中 · 最快模式', cls: 'streaming' }
        : { label: '处理中', cls: 'streaming' }
    case 'done':
      return { label: '处理完成', cls: 'done' }
    case 'error':
      return { label: '错误', cls: 'error' }
  }
})

const asrLabel = computed(() => {
  switch (store.asrMode) {
    case 'none':
      return '无 ASR'
    case 'offline':
      return '离线 ASR'
    case 'streaming':
      return '流式 ASR'
  }
})

const processedText = computed(() => {
  const done = store.phase === 'done'
  const total = done ? totalDur.value : store.clip?.duration ?? 0
  return `${fmtTime(store.progressT)} / ${fmtTime(total)}`
})

const confText = computed(() => {
  const c = avgConfidence.value
  return c === null ? '—' : `${(c * 100).toFixed(0)}%`
})
</script>

<template>
  <footer class="statusbar">
    <div class="st-left">
      <span class="st-dot" :class="phaseMeta.cls"></span>
      <span class="st-label">{{ phaseMeta.label }}</span>
      <span v-if="store.lastSpeakers > 0 && store.phase === 'done'" class="st-extra">
        检出 {{ store.lastSpeakers }} 位说话人
      </span>
    </div>

    <div class="st-mid">
      <span class="st-item">模式：{{ asrLabel }}</span>
      <span class="st-item">转写 {{ store.events.length }} 段</span>
      <span class="st-item" title="平均置信度">置信度 {{ confText }}</span>
    </div>

    <div class="st-right">
      <span class="st-item mono">{{ processedText }}</span>
      <span class="st-item mono" title="各说话人累计时长">
        {{ speakerSummary }}
      </span>
    </div>
  </footer>
</template>

<style scoped>
.statusbar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 14px;
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  font-size: 12.5px;
  color: var(--text-dim);
  flex-wrap: wrap;
}

.st-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.st-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-faint);
}

.st-dot.connecting { background: var(--warn); animation: pulse 1s infinite; }
.st-dot.streaming { background: var(--accent); animation: pulse 1.4s infinite; }
.st-dot.done { background: var(--ok); }
.st-dot.error { background: var(--danger); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.st-label {
  font-weight: 600;
  color: var(--text);
}

.st-extra {
  color: var(--ok);
}

.st-mid {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.st-item {
  white-space: nowrap;
}

.mono {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}

.st-right {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .st-mid {
    display: none;
  }
}
</style>
