<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppHeader from './components/AppHeader.vue'
import SourceBar from './components/SourceBar.vue'
import TransportBar from './components/TransportBar.vue'
import Timeline from './components/Timeline.vue'
import Transcript from './components/Transcript.vue'
import SidePanel from './components/SidePanel.vue'
import {
  session,
  begin,
  sendChunk,
  sendEnd,
  sendStop,
  closeWs,
  reset,
  fetchModels,
} from './composables/session'
import {
  playing,
  rate,
  position,
  duration,
  hasAudio,
  loadAudio,
  stopAudio,
  togglePlay,
  setRate,
  onAudioEnded,
} from './composables/playback'
import { micSeconds, startMic, stopMic } from './composables/mic'
import { t } from './composables/i18n'
import { CHUNK, TARGET_RATE, decodeAudio, toMono16k } from './utils/audio'
import type { SourceKind } from './types'

/* ---------------- 音频源状态 ---------------- */
const sourceKind = ref<SourceKind>('demo')
const demoUrl = ref('')
const demoName = ref('')
const uploadName = ref('')
/** 示例/上传统一为 16k 单声道 */
const samples16k = ref<Float32Array | null>(null)
const waveform = ref<Float32Array | null>(null)

const demoOptions = computed(() =>
  session.models
    ? Object.entries(session.models.demo_wavs).map(([name, url]) => ({ name, url }))
    : [],
)

/* ---------------- 流程控制 ---------------- */
let sendTimer = 0
let sentSamples = 0
let endSent = false
let micQueue: Float32Array[] = []
let micTimer = 0
const banner = ref('')

const locked = computed(
  () => session.phase === 'connecting' || session.phase === 'processing',
)

const modeUsable = computed(() => {
  const m = session.models
  if (!m) return false
  if (session.asrMode === 'streaming') return m.asr_streaming_ready
  if (session.asrMode === 'offline') return m.asr_offline_ready
  return true
})

const canStart = computed(() => {
  if (!session.models?.models_ready || !modeUsable.value) return false
  if (sourceKind.value === 'demo') return !!demoUrl.value
  if (sourceKind.value === 'upload') return !!samples16k.value
  return true
})

/* ---------------- 源切换 ---------------- */
function onPickDemo() {
  sourceKind.value = 'demo'
  if (!demoUrl.value && demoOptions.value.length) {
    demoUrl.value = demoOptions.value[0].url
    demoName.value = demoOptions.value[0].name
  }
}
function onPickUpload() {
  sourceKind.value = 'upload'
}
function onDemoChange(url: string) {
  demoUrl.value = url
  demoName.value = demoOptions.value.find((o) => o.url === url)?.name ?? ''
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  sourceKind.value = 'upload'
  uploadName.value = file.name
  try {
    const buf = await decodeAudio(await file.arrayBuffer())
    samples16k.value = toMono16k(buf)
    waveform.value = samples16k.value
    session.error = null
  } catch {
    session.error = t('errors.decodeFailed')
    session.phase = 'error'
  }
}

/* ---------------- 发送节奏：与回放位置同步 ---------------- */
function startSending() {
  clearSending()
  sendTimer = window.setInterval(() => {
    if (session.phase !== 'processing' || !playing.value) return
    const total = samples16k.value?.length ?? 0
    if (!total || position.value * TARGET_RATE <= sentSamples) return
    const target = Math.min(Math.floor(position.value * TARGET_RATE), total)
    while (sentSamples + CHUNK <= target) {
      sendChunk(samples16k.value!.slice(sentSamples, sentSamples + CHUNK))
      sentSamples += CHUNK
    }
    if (sentSamples < target) {
      sendChunk(samples16k.value!.slice(sentSamples, target))
      sentSamples = target
    }
  }, 60)
}
function clearSending() {
  if (sendTimer) {
    clearInterval(sendTimer)
    sendTimer = 0
  }
}

/** 音频自然播完：补发剩余样本并通知后端结束 */
function finishAndSendEnd() {
  clearSending()
  if (session.phase !== 'processing') return
  const total = samples16k.value?.length ?? 0
  if (samples16k.value && sentSamples < total) {
    sendChunk(samples16k.value.slice(sentSamples, total))
    sentSamples = total
  }
  if (!endSent) {
    endSent = true
    sendEnd()
  }
}
onAudioEnded(finishAndSendEnd)

function flushMic() {
  if (session.phase !== 'processing') return
  for (const c of micQueue) sendChunk(c)
  micQueue = []
}

/* ---------------- 会话流程 ---------------- */
async function startSession() {
  if (locked.value) return
  stopAudio()
  reset()
  session.error = null
  try {
    if (sourceKind.value === 'mic') {
      await begin(session.asrMode, 'mic', t('source.micName'))
      micQueue = []
      await startMic((c) => micQueue.push(c))
      micTimer = window.setInterval(flushMic, 150)
    } else {
      if (!samples16k.value) await loadFileSource()
      await begin(session.asrMode, sourceKind.value, sourceName())
      loadAudio(samples16k.value!)
      sentSamples = 0
      endSent = false
      startSending()
      togglePlay() // 播放即开始发送
    }
  } catch (e) {
    clearSending()
    stopMic()
    session.phase = 'error'
    session.error = e instanceof Error ? e.message : String(e)
  }
}

async function loadFileSource() {
  const url = demoUrl.value
  if (!url) throw new Error(t('errors.needDemo'))
  const res = await fetch(url)
  if (!res.ok) throw new Error(t('errors.demoLoadFailed'))
  const buf = await decodeAudio(await res.arrayBuffer())
  samples16k.value = toMono16k(buf)
  waveform.value = samples16k.value
}

function sourceName(): string {
  if (sourceKind.value === 'mic') return t('source.micName')
  if (sourceKind.value === 'upload') return uploadName.value || t('source.uploadFallback')
  return demoName.value || t('source.demoFallback')
}

function stopMicRecording() {
  sendEnd()
  clearInterval(micTimer)
  micTimer = 0
  stopMic()
}

function cancelSession() {
  sendStop()
  closeWs()
  clearSending()
  if (micTimer) {
    clearInterval(micTimer)
    micTimer = 0
  }
  stopMic()
  stopAudio()
  reset()
}

function onPrimary() {
  if (session.phase === 'processing') {
    if (sourceKind.value === 'mic') stopMicRecording()
    else cancelSession()
    return
  }
  if (session.phase === 'connecting') return
  void startSession()
}

watch(
  () => session.phase,
  (p) => {
    if (p === 'done') {
      closeWs()
      clearSending()
      if (micTimer) {
        clearInterval(micTimer)
        micTimer = 0
      }
      stopMic()
    }
  },
)

watch(
  () => session.models,
  (m) => {
    if (!m) return
    if (!demoUrl.value && Object.keys(m.demo_wavs).length) {
      const [name, url] = Object.entries(m.demo_wavs)[0]
      demoUrl.value = url
      demoName.value = name
    }
    if (session.asrMode === 'streaming' && !m.asr_streaming_ready) {
      session.asrMode = m.asr_offline_ready ? 'offline' : 'none'
    } else if (session.asrMode === 'offline' && !m.asr_offline_ready) {
      session.asrMode = m.asr_streaming_ready ? 'streaming' : 'none'
    }
  },
)

onMounted(() => {
  void fetchModels().catch(() => {
    banner.value = t('errors.modelsFetch')
  })
})

onBeforeUnmount(() => {
  clearSending()
  if (micTimer) clearInterval(micTimer)
  stopMic()
  closeWs()
})
</script>

<template>
  <div class="app">
    <AppHeader :locked="locked" />

    <div v-if="banner" class="banner">{{ banner }}</div>

    <main class="stage">
      <div class="deck">
        <SourceBar
          :phase="session.phase"
          :kind="sourceKind"
          :demo-options="demoOptions"
          :demo-url="demoUrl"
          :demo-name="demoName"
          :upload-name="uploadName"
          :can-start="canStart"
          :mic-seconds="micSeconds"
          @pick-demo="onPickDemo"
          @pick-upload="onPickUpload"
          @pick-mic="sourceKind = 'mic'"
          @demo="onDemoChange"
          @file="onFileChange"
          @primary="onPrimary"
        />
        <TransportBar
          :phase="session.phase"
          :kind="sourceKind"
          :playing="playing"
          :rate="rate"
          :position="position"
          :duration="duration"
          :has-audio="hasAudio"
          @toggle="togglePlay"
          @stop="stopAudio"
          @rate="setRate"
        />
      </div>

      <Timeline :waveform="waveform" />

      <div class="lower">
        <Transcript />
        <SidePanel />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.banner {
  flex-shrink: 0;
  padding: 8px 18px;
  background: rgba(255, 107, 129, 0.1);
  border-bottom: 1px solid rgba(255, 107, 129, 0.3);
  color: var(--bad);
  font-size: 12.5px;
}
.stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 16px 14px;
}
.deck {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  min-width: 0;
}
.deck > :first-child {
  flex: 1;
  min-width: 0;
}
.lower {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 10px;
}
.lower > :first-child {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1060px) {
  .lower > :last-child {
    width: 236px;
  }
}
@media (max-width: 940px) {
  body {
    overflow: auto;
  }
  .stage {
    overflow: visible;
  }
  .deck {
    flex-direction: column;
  }
  .lower {
    flex-direction: column;
    overflow: visible;
  }
  .lower > :last-child {
    width: auto;
    flex-direction: row;
    align-items: stretch;
  }
  .lower > :last-child > * {
    flex: 1;
  }
}
</style>
