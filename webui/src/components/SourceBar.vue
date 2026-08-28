<script setup lang="ts">
import { computed } from 'vue'
import type { Phase, SourceKind } from '../types'
import { fmtClock } from '../utils/time'
import { t } from '../composables/i18n'

const props = defineProps<{
  phase: Phase
  kind: SourceKind
  demoOptions: { name: string; url: string }[]
  demoUrl: string
  demoName: string
  uploadName: string
  canStart: boolean
  micSeconds: number
}>()

const emit = defineEmits<{
  (e: 'pick-demo'): void
  (e: 'pick-upload'): void
  (e: 'pick-mic'): void
  (e: 'demo', url: string): void
  (e: 'file', ev: Event): void
  (e: 'primary'): void
}>()

const busy = computed(() => props.phase === 'connecting' || props.phase === 'processing')

const primaryLabel = computed(() => {
  switch (props.phase) {
    case 'connecting':
      return t('action.connecting')
    case 'processing':
      return props.kind === 'mic' ? t('action.stopRecording') : t('action.abort')
    case 'done':
      return t('action.restart')
    case 'error':
      return t('action.retry')
    default:
      return t('action.start')
  }
})
</script>

<template>
  <div class="srcbar">
    <div class="tabs" role="tablist" :aria-label="t('source.tabsLabel')">
      <button
        class="tab"
        :class="{ on: kind === 'demo' }"
        :disabled="busy"
        @click="emit('pick-demo')"
      >
        {{ t('source.demo') }}
      </button>
      <button
        class="tab"
        :class="{ on: kind === 'upload' }"
        :disabled="busy"
        @click="emit('pick-upload')"
      >
        {{ t('source.upload') }}
      </button>
      <button
        class="tab"
        :class="{ on: kind === 'mic' }"
        :disabled="busy"
        @click="emit('pick-mic')"
      >
        {{ t('source.mic') }}
      </button>
    </div>

    <div class="ctrl">
      <!-- 示例 -->
      <div v-if="kind === 'demo'" class="field">
        <select
          class="demo-sel"
          :value="demoUrl"
          :disabled="busy || !demoOptions.length"
          @change="emit('demo', ($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>
            {{ demoOptions.length ? t('source.placeholder') : t('source.noDemo') }}
          </option>
          <option v-for="o in demoOptions" :key="o.url" :value="o.url">{{ o.name }}</option>
        </select>
        <span v-if="demoName" class="note mono">{{ demoName }}</span>
      </div>

      <!-- 上传 -->
      <div v-else-if="kind === 'upload'" class="field">
        <label class="file-btn" :class="{ disabled: busy }">
          {{ t('source.chooseFile') }}
          <input
            type="file"
            accept="audio/*,.wav,.mp3,.flac,.ogg,.m4a,.aac"
            :disabled="busy"
            @change="emit('file', $event)"
          />
        </label>
        <span class="note" :class="{ 'note-dim': !uploadName }">
          {{ uploadName || t('source.fileHint') }}
        </span>
      </div>

      <!-- 录音 -->
      <div v-else class="field">
        <span class="mic-hint">
          <i class="mic-dot" :class="{ live: phase === 'processing' }" />
          {{ t('source.micHint') }}
        </span>
        <span v-if="phase === 'processing'" class="mic-timer mono">{{ fmtClock(micSeconds) }}</span>
      </div>

      <button
        class="primary"
        :class="phase"
        :disabled="phase === 'idle' && !canStart"
        @click="emit('primary')"
      >
        {{ primaryLabel }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.srcbar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: var(--bg-1);
  border: 1px solid var(--line-1);
  border-radius: var(--radius);
}
.tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 99px;
  background: var(--bg-2);
  border: 1px solid var(--line-1);
}
.tab {
  height: 26px;
  padding: 0 14px;
  border-radius: 99px;
  font-size: 12.5px;
  color: var(--ink-mid);
  transition: all 0.18s var(--ease);
}
.tab:hover:not(:disabled) {
  color: var(--ink-hi);
}
.tab.on {
  background: var(--bg-3);
  color: var(--ink-hi);
  box-shadow: inset 0 0 0 1px var(--line-2);
}
.tab:disabled {
  opacity: 0.4;
}
.ctrl {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.field {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.demo-sel {
  max-width: 280px;
  height: 32px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line-2);
  background: var(--bg-2);
  color: var(--ink-hi);
  font-size: 13px;
  outline: none;
}
.demo-sel:focus {
  border-color: var(--accent);
}
.file-btn {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--line-2);
  background: var(--bg-2);
  color: var(--ink-hi);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s var(--ease);
}
.file-btn:hover:not(.disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.file-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.file-btn input {
  display: none;
}
.note {
  font-size: 12px;
  color: var(--ink-mid);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.note-dim {
  color: var(--ink-low);
}
.mic-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-mid);
}
.mic-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ink-low);
}
.mic-dot.live {
  background: var(--bad);
  animation: blink 1s ease-in-out infinite;
}
.mic-timer {
  font-size: 15px;
  font-weight: 600;
  color: var(--bad);
  letter-spacing: 0.06em;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.primary {
  flex-shrink: 0;
  height: 34px;
  padding: 0 22px;
  border-radius: 99px;
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #071018;
  background: var(--accent);
  box-shadow: 0 6px 18px rgba(90, 162, 255, 0.28);
  transition: all 0.18s var(--ease);
}
.primary:hover:not(:disabled) {
  filter: brightness(1.08);
  transform: translateY(-1px);
}
.primary:disabled {
  opacity: 0.4;
  box-shadow: none;
}
.primary.processing {
  background: var(--bad);
  color: #fff;
  box-shadow: 0 6px 18px rgba(255, 107, 129, 0.25);
}
.primary.connecting {
  background: var(--bg-3);
  color: var(--ink-mid);
  box-shadow: none;
}
</style>
