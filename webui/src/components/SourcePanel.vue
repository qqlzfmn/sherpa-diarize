<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { store } from '../store'
import { fmtTime } from '../types'
import type { PlayRate, SourceKind } from '../types'
import {
  loadDemoWav,
  loadUploadFile,
  loadModels,
  startRec,
  stopRec,
  startProcessing,
  togglePlay,
  changeRate,
} from '../controller'

const tabs: { key: SourceKind; label: string }[] = [
  { key: 'demo', label: '示例音频' },
  { key: 'upload', label: '上传音频' },
  { key: 'record', label: '录音' },
]

const demoOptions = computed(() => {
  const w = store.models?.demo_wavs ?? {}
  return Object.entries(w).map(([name, url]) => ({ name, url }))
})

const selectedDemo = ref('')

watch(demoOptions, (opts) => {
  if (opts.length > 0 && !opts.some((o) => o.name === selectedDemo.value)) {
    selectedDemo.value = opts[0].name
  }
})

const rates: PlayRate[] = [1, 2, 4, 8, 0]

function rateLabel(r: PlayRate): string {
  return r === 0 ? '最快' : `${r}x`
}

function onTab(k: SourceKind): void {
  store.sourceKind = k
}

function loadSelected(): void {
  const opt = demoOptions.value.find((o) => o.name === selectedDemo.value)
  if (opt) void loadDemoWav(opt.name, opt.url)
}

function onPickFile(e: Event): void {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) void loadUploadFile(file)
  input.value = ''
}

const processingNow = computed(
  () => store.phase === 'connecting' || store.phase === 'ready' || store.phase === 'streaming',
)

const playLabel = computed(() => {
  if (processingNow.value) return store.playing && !store.isTurbo ? '⏸ 暂停' : '▶ 继续'
  return '▶ 播放'
})

function onPlayClick(): void {
  if (processingNow.value) {
    togglePlay()
  } else {
    void startProcessing()
  }
}
</script>

<template>
  <section class="panel source-panel">
    <div class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: store.sourceKind === t.key }"
        @click="onTab(t.key)"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="source-body">
      <!-- 示例音频 -->
      <div v-if="store.sourceKind === 'demo'" class="src-row">
        <template v-if="store.models">
          <select v-model="selectedDemo">
            <option v-if="demoOptions.length === 0" value="">（无可用示例）</option>
            <option v-for="o in demoOptions" :key="o.name" :value="o.name">
              {{ o.name }}
            </option>
          </select>
          <button :disabled="demoOptions.length === 0 || store.clipLoading" @click="loadSelected">
            加载
          </button>
        </template>
        <template v-else>
          <span class="hint dim">后端模型信息不可用</span>
          <button @click="void loadModels()">重试</button>
        </template>
        <span v-if="store.clipLoading" class="loading">加载解码中…</span>
      </div>

      <!-- 上传音频 -->
      <div v-else-if="store.sourceKind === 'upload'" class="src-row">
        <label class="dropzone" :class="{ on: store.clipLoading }">
          <input type="file" accept="audio/*,.wav,.mp3,.ogg,.flac,.m4a" @change="onPickFile" />
          <span v-if="store.clipLoading">解码中…</span>
          <span v-else>点击选择本地音频（wav / mp3 / ogg / m4a）</span>
        </label>
      </div>

      <!-- 录音 -->
      <div v-else class="src-row">
        <template v-if="!store.isRecording">
          <button class="rec-btn" @click="void startRec()">● 开始录音</button>
          <span class="hint dim">需授予麦克风权限；采样 16kHz 单声道</span>
        </template>
        <template v-else>
          <span class="rec-live">
            <span class="rec-dot"></span>
            录音中 {{ fmtTime(store.recordDuration) }}
          </span>
          <button class="rec-btn stop" @click="stopRec()">■ 停止录音</button>
        </template>
      </div>

      <span v-if="store.clipError" class="clip-error">{{ store.clipError }}</span>
    </div>

    <!-- 已加载片段 + 播放控制 -->
    <div v-if="store.clip" class="clipbar">
      <div class="clip-info">
        <span class="clip-name" :title="store.clip.name">{{ store.clip.name }}</span>
        <span class="clip-dur">{{ fmtTime(store.pos) }} / {{ fmtTime(store.clip.duration) }}</span>
      </div>
      <div class="play-ctl">
        <button
          class="play-btn"
          :disabled="store.isRecording"
          @click="onPlayClick"
        >
          {{ playLabel }}
        </button>
        <div class="rates">
          <button
            v-for="r in rates"
            :key="r"
            class="rate-btn"
            :class="{ active: store.rate === r }"
            :disabled="store.isRecording"
            @click="changeRate(r)"
          >
            {{ rateLabel(r) }}
          </button>
        </div>
        <span v-if="store.isTurbo" class="turbo-tag">最快模式（无声音）</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.source-panel {
  flex: none;
}

.tabs {
  display: flex;
  gap: 2px;
  padding: 8px 12px 0;
}

.tab {
  border: none;
  background: transparent;
  color: var(--text-dim);
  padding: 6px 16px;
  border-radius: 8px 8px 0 0;
  position: relative;
}

.tab.active {
  color: var(--text);
  background: var(--card-2);
}

.tab.active::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: -1px;
  height: 2px;
  background: var(--accent);
  border-radius: 2px;
}

.source-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 16px 12px;
  background: var(--card-2);
  border-top: 1px solid var(--border-soft);
  border-radius: 0 0 var(--radius) var(--radius);
}

.src-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 34px;
  flex-wrap: wrap;
}

.hint {
  font-size: 12.5px;
  color: var(--text);
}

.hint.dim {
  color: var(--text-dim);
}

.loading {
  font-size: 12.5px;
  color: var(--accent);
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.dropzone {
  display: inline-flex;
  align-items: center;
  padding: 8px 22px;
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.15s ease;
  background: rgba(34, 211, 238, 0.03);
}

.dropzone:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.dropzone.on {
  opacity: 0.6;
}

.rec-btn {
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.5);
  color: var(--danger);
  font-weight: 600;
  padding: 7px 18px;
}

.rec-btn:hover:not(:disabled) {
  color: var(--danger);
  border-color: var(--danger);
  background: rgba(248, 113, 113, 0.2);
}

.rec-btn.stop {
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.5);
  color: var(--ok);
}

.rec-live {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-variant-numeric: tabular-nums;
  font-family: var(--mono);
  font-size: 14px;
  color: var(--danger);
}

.rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--danger);
  animation: pulse 1s infinite;
}

.clip-error {
  color: var(--danger);
  font-size: 12.5px;
}

.clipbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 16px;
  border-top: 1px solid var(--border-soft);
  flex-wrap: wrap;
}

.clip-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}

.clip-name {
  font-size: 13px;
  font-weight: 600;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clip-dur {
  font-family: var(--mono);
  font-size: 12.5px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}

.play-ctl {
  display: flex;
  align-items: center;
  gap: 10px;
}

.play-btn {
  min-width: 84px;
}

.rates {
  display: flex;
  gap: 4px;
}

.rate-btn {
  padding: 5px 11px;
  font-size: 12.5px;
  font-family: var(--mono);
}

.rate-btn.active {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: rgba(34, 211, 238, 0.5);
}

.turbo-tag {
  font-size: 11.5px;
  color: var(--warn);
  border: 1px solid rgba(251, 191, 36, 0.4);
  border-radius: 999px;
  padding: 2px 10px;
}
</style>
