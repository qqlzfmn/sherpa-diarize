import { reactive, computed } from 'vue'
import type {
  AsrMode,
  Clip,
  ModelsInfo,
  Phase,
  PlayRate,
  SourceKind,
  TurnEvent,
} from './types'
import { CHUNK_DUR } from './types'

/* ------------------------------------------------------------------ */
/* 全局响应式状态（单例，组件共享）                                      */
/* ------------------------------------------------------------------ */

interface StoreState {
  models: ModelsInfo | null
  modelsError: string | null

  sourceKind: SourceKind
  asrMode: AsrMode

  clip: Clip | null
  clipLoading: boolean
  clipError: string | null

  isRecording: boolean
  recordDuration: number

  phase: Phase
  events: TurnEvent[]
  partialText: string | null
  progressT: number
  lastSpeakers: number
  error: string | null

  playing: boolean
  rate: PlayRate
  pos: number
  isTurbo: boolean
}

export const store = reactive<StoreState>({
  models: null,
  modelsError: null,

  sourceKind: 'demo',
  asrMode: 'streaming',

  clip: null,
  clipLoading: false,
  clipError: null,

  isRecording: false,
  recordDuration: 0,

  phase: 'idle',
  events: [],
  partialText: null,
  progressT: 0,
  lastSpeakers: 0,
  error: null,

  playing: false,
  rate: 1,
  pos: 0,
  isTurbo: false,
})

/** 当前会话期间总时长（处理中=已发送/播放位置；完成后=总时长） */
export const totalDur = computed(() => {
  if (store.phase === 'done') {
    const last = store.events[store.events.length - 1]
    return last ? Math.max(last.end, store.progressT) : store.progressT
  }
  return store.clip ? store.clip.duration : store.progressT
})

/** 说话人统计：颜色 + 总时长 + 段数 */
export const speakerStats = computed(() => {
  const map = new Map<number, { duration: number; turns: number }>()
  for (const ev of store.events) {
    const it = map.get(ev.speaker) ?? { duration: 0, turns: 0 }
    it.duration += ev.end - ev.start
    it.turns += 1
    map.set(ev.speaker, it)
  }
  return [...map.entries()]
    .sort((a, b) => b[1].duration - a[1].duration)
    .map(([speaker, s]) => ({ speaker, ...s }))
})

export const avgConfidence = computed(() => {
  if (store.events.length === 0) return null
  const sum = store.events.reduce((a, e) => a + e.confidence, 0)
  return sum / store.events.length
})

/* ------------------------------------------------------------------ */
/* 状态操作                                                            */
/* ------------------------------------------------------------------ */

export function setModels(m: ModelsInfo): void {
  store.models = m
  store.modelsError = null
  if (!m.asr_streaming_ready && m.asr_offline_ready && store.asrMode === 'streaming') {
    store.asrMode = 'offline'
  }
  if (!m.asr_streaming_ready && !m.asr_offline_ready) {
    store.asrMode = 'none'
  }
}

export function setModelsError(msg: string): void {
  store.modelsError = msg
}

export function setClip(clip: Clip | null): void {
  store.clip = clip
  store.clipError = null
  store.pos = 0
  store.rate = 1
  store.playing = false
  store.isTurbo = false
}

export function setClipLoading(v: boolean): void {
  store.clipLoading = v
}

export function setClipError(msg: string | null): void {
  store.clipError = msg
}

export function resetSession(): void {
  store.events = []
  store.partialText = null
  store.progressT = 0
  store.lastSpeakers = 0
  store.error = null
  store.phase = 'idle'
  store.pos = 0
  store.playing = false
}

export function pushEvent(ev: Omit<TurnEvent, 'id'>): void {
  store.events.push({ ...ev, id: store.events.length })
}

export function setPartial(text: string | null): void {
  store.partialText = text
}

export function setProgress(t: number): void {
  store.progressT = Math.max(store.progressT, t)
}

export function setPhase(p: Phase): void {
  store.phase = p
}

export function setError(msg: string | null): void {
  store.error = msg
}

export function setPos(p: number): void {
  store.pos = p
}

export function setPlaying(v: boolean): void {
  store.playing = v
}

export function setRate(r: PlayRate): void {
  store.rate = r
}

export function setTurbo(v: boolean): void {
  store.isTurbo = v
}

/** 辅助：当前播放位置对应的分块索引（用于发送进度显示） */
export function chunkIndexAtPos(pos: number): number {
  return Math.floor(pos / CHUNK_DUR)
}
