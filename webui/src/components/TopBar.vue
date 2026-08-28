<script setup lang="ts">
import { computed } from 'vue'
import { store } from '../store'
import type { AsrMode } from '../types'
import { startProcessing, stopProcessing, setAsrMode } from '../controller'

const phaseText = computed(() => {
  switch (store.phase) {
    case 'idle':
      return '就绪'
    case 'connecting':
      return '连接中…'
    case 'ready':
      return '准备发送'
    case 'streaming':
      return '处理中'
    case 'done':
      return '完成'
    case 'error':
      return '错误'
  }
})

const phaseClass = computed(() => `dot-${store.phase}`)

const busy = computed(
  () => store.phase === 'connecting' || store.phase === 'ready' || store.phase === 'streaming',
)

const canStart = computed(
  () =>
    !!store.clip &&
    !store.isRecording &&
    store.phase !== 'connecting' &&
    store.phase !== 'ready' &&
    store.phase !== 'streaming',
)

const actionLabel = computed(() => {
  if (store.phase === 'connecting' || store.phase === 'ready') return '连接中…'
  if (store.phase === 'streaming') return '停止'
  if (store.phase === 'done') return '再次处理'
  if (store.phase === 'error') return '重试'
  return '开始处理'
})

function onAction(): void {
  if (busy.value) {
    stopProcessing()
  } else {
    void startProcessing()
  }
}

function onMode(mode: AsrMode): void {
  if (busy.value) return
  setAsrMode(mode)
}

function modeDisabled(mode: AsrMode): boolean {
  if (!store.models) return false
  if (mode === 'offline') return !store.models.asr_offline_ready
  if (mode === 'streaming') return !store.models.asr_streaming_ready
  return !store.models.models_ready
}
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <div class="logo">
        <span class="logo-wave w1"></span>
        <span class="logo-wave w2"></span>
        <span class="logo-wave w3"></span>
        <span class="logo-wave w4"></span>
      </div>
      <div class="brand-text">
        <h1>Sherpa Diarize</h1>
        <p>实时流式说话人分离 · Web 控制台</p>
      </div>
    </div>

    <div class="asr-group" title="后端模型就绪状态决定可用项">
      <span class="asr-label">ASR</span>
      <div class="seg">
        <button
          v-for="m in (['none', 'offline', 'streaming'] as AsrMode[])"
          :key="m"
          class="seg-btn"
          :class="{ active: store.asrMode === m }"
          :disabled="busy || modeDisabled(m)"
          :title="modeDisabled(m) ? '该 ASR 模型未就绪' : ''"
          @click="onMode(m)"
        >
          {{ m === 'none' ? '无' : m === 'offline' ? '离线' : '流式' }}
        </button>
      </div>
    </div>

    <div class="phase-badge" :class="phaseClass">
      <span class="phase-dot"></span>
      {{ phaseText }}
    </div>

    <button
      class="action-btn"
      :class="{ danger: busy }"
      :disabled="!canStart && !busy && store.phase !== 'streaming'"
      @click="onAction"
    >
      {{ actionLabel }}
    </button>
  </header>
</template>

<style scoped>
.topbar {
  flex: none;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 6px 4px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-right: auto;
}

.logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.22), rgba(167, 139, 250, 0.22));
  border: 1px solid rgba(34, 211, 238, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.logo-wave {
  width: 3px;
  border-radius: 2px;
  background: var(--accent);
  animation: eq 1.1s ease-in-out infinite;
}

.logo-wave.w1 { height: 10px; animation-delay: 0s; }
.logo-wave.w2 { height: 20px; animation-delay: 0.18s; }
.logo-wave.w3 { height: 14px; animation-delay: 0.36s; }
.logo-wave.w4 { height: 8px; animation-delay: 0.54s; }

@keyframes eq {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

.brand-text h1 {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.brand-text p {
  font-size: 12px;
  color: var(--text-dim);
}

.asr-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.asr-label {
  font-size: 12px;
  color: var(--text-dim);
  letter-spacing: 0.08em;
}

.seg {
  display: flex;
  background: var(--card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 2px;
}

.seg-btn {
  border: none;
  background: transparent;
  padding: 4px 14px;
  font-size: 13px;
  color: var(--text-dim);
  border-radius: 6px;
}

.seg-btn.active {
  background: var(--accent-soft);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.35);
}

.phase-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: var(--text-dim);
  padding: 5px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--card);
}

.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-faint);
}

.dot-idle .phase-dot { background: var(--text-faint); }
.dot-connecting .phase-dot { background: var(--warn); animation: pulse 1s infinite; }
.dot-ready .phase-dot { background: var(--warn); }
.dot-streaming .phase-dot { background: var(--accent); animation: pulse 1.4s infinite; }
.dot-done .phase-dot { background: var(--ok); }
.dot-error .phase-dot { background: var(--danger); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.action-btn {
  flex: none;
  min-width: 116px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.9), rgba(56, 189, 248, 0.9));
  border: none;
  color: #051014;
  font-weight: 700;
  font-size: 14px;
  padding: 9px 22px;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(34, 211, 238, 0.25);
}

.action-btn:hover:not(:disabled) {
  color: #051014;
  filter: brightness(1.1);
}

.action-btn.danger {
  background: rgba(248, 113, 113, 0.16);
  color: var(--danger);
  border: 1px solid rgba(248, 113, 113, 0.45);
  box-shadow: none;
}

@media (max-width: 900px) {
  .asr-group {
    display: none;
  }
}
</style>
