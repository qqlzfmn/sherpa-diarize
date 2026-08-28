<script setup lang="ts">
import { computed } from 'vue'
import { session } from '../composables/session'
import type { AsrMode } from '../types'
import StatusChip from './StatusChip.vue'

const props = defineProps<{ locked: boolean }>()

const modes: { value: AsrMode; label: string; disabled: boolean; hint: string }[] = [
  { value: 'none', label: '无 ASR', disabled: false, hint: '仅说话人分离，不做转写' },
  {
    value: 'offline',
    label: '离线',
    disabled: !session.models?.asr_offline_ready,
    hint: session.models?.asr_offline_ready ? '整句离线转写' : '离线模型未就绪',
  },
  {
    value: 'streaming',
    label: '流式',
    disabled: !session.models?.asr_streaming_ready,
    hint: session.models?.asr_streaming_ready ? '实时增量识别（含预览）' : '流式模型未就绪',
  },
]

const modelsBad = computed(() => session.models && !session.models.models_ready)
</script>

<template>
  <header class="head">
    <div class="brand">
      <div class="mark" aria-hidden="true">
        <i class="b b1" /><i class="b b2" /><i class="b b3" />
      </div>
      <div class="brand-txt">
        <h1>声分</h1>
        <p>sherpa-diarize · 实时说话人分离与转写</p>
      </div>
    </div>

    <div class="right">
      <span class="edge-chip" title="模型与推理全部在本机完成，音频不出设备">
        <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
          <circle cx="6" cy="6" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" />
          <circle cx="6" cy="6" r="1.6" fill="currentColor" />
        </svg>
        端侧运行
      </span>

      <div class="mode" role="group" aria-label="ASR 模式">
        <span class="mode-label">识别模式</span>
        <button
          v-for="m in modes"
          :key="m.value"
          class="mode-btn"
          :class="{ on: session.asrMode === m.value }"
          :disabled="locked || m.disabled"
          :title="m.hint"
          @click="session.asrMode = m.value"
        >
          {{ m.label }}
        </button>
      </div>

      <StatusChip :phase="session.phase" />
    </div>

    <div v-if="modelsBad" class="warn-banner">
      ⚠ 基础模型未就绪（VAD / 说话人嵌入缺失），请先运行
      <code>python3 scripts/download_models.py</code>
    </div>
  </header>
</template>

<style scoped>
.head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  height: 58px;
  padding: 0 18px;
  border-bottom: 1px solid var(--line-1);
  background: linear-gradient(180deg, rgba(17, 24, 38, 0.6), rgba(12, 16, 23, 0.4));
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.mark {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  width: 34px;
  height: 34px;
  padding: 7px 6px;
  border-radius: 10px;
  background: var(--bg-2);
  border: 1px solid var(--line-2);
  box-shadow: var(--shadow);
}
.b {
  width: 5px;
  border-radius: 2px;
}
.b1 {
  height: 11px;
  background: #ffb454;
}
.b2 {
  height: 20px;
  background: #54c8ff;
}
.b3 {
  height: 15px;
  background: #b98cff;
}
.brand-txt h1 {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.14em;
  line-height: 1.1;
}
.brand-txt p {
  font-size: 11px;
  color: var(--ink-low);
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.edge-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 10px;
  border-radius: 99px;
  background: rgba(94, 240, 176, 0.08);
  border: 1px solid rgba(94, 240, 176, 0.25);
  color: var(--good);
  font-size: 11.5px;
  white-space: nowrap;
}
.mode {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 30px;
  padding: 3px;
  border-radius: 99px;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
}
.mode-label {
  font-size: 11px;
  color: var(--ink-low);
  padding: 0 6px 0 8px;
  letter-spacing: 0.08em;
}
.mode-btn {
  height: 22px;
  padding: 0 12px;
  border-radius: 99px;
  font-size: 12px;
  color: var(--ink-mid);
  transition: all 0.18s var(--ease);
}
.mode-btn:hover:not(:disabled) {
  color: var(--ink-hi);
}
.mode-btn.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.mode-btn:disabled {
  opacity: 0.35;
}
.warn-banner {
  position: absolute;
  left: 50%;
  top: 62px;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  background: rgba(255, 209, 102, 0.1);
  border: 1px solid rgba(255, 209, 102, 0.35);
  color: var(--warn);
  font-size: 12.5px;
  white-space: nowrap;
}
.warn-banner code {
  font-family: var(--font-mono);
  background: rgba(255, 209, 102, 0.12);
  padding: 1px 6px;
  border-radius: 5px;
}

@media (max-width: 1080px) {
  .brand-txt p {
    display: none;
  }
}
@media (max-width: 860px) {
  .edge-chip {
    display: none;
  }
}
</style>
