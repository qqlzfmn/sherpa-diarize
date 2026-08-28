/**
 * 文件回放：示例/上传音频的播放、暂停、倍速与位置跟踪。
 * 播放节奏即发送节奏 —— 上层按 position 切音频块发给后端。
 */
import { ref } from 'vue'
import { TARGET_RATE, resample } from '../utils/audio'

let ctx: AudioContext | null = null
let buffer: AudioBuffer | null = null
let src: AudioBufferSourceNode | null = null
let segBase = 0 // 本段起始内容位置（秒）
let segStartAt = 0 // 本段起始的 ctx.currentTime
let raf = 0
let endedCb: (() => void) | null = null

export const playing = ref(false)
export const rate = ref(1)
export const position = ref(0)
export const duration = ref(0)
export const hasAudio = ref(false)

function ensureCtx(): AudioContext {
  if (!ctx) ctx = new AudioContext()
  return ctx
}

export function loadAudio(samples16k: Float32Array) {
  const ac = ensureCtx()
  const audio = resample(samples16k, TARGET_RATE, ac.sampleRate)
  buffer = ac.createBuffer(1, audio.length, ac.sampleRate)
  buffer.copyToChannel(audio, 0)
  duration.value = samples16k.length / TARGET_RATE
  position.value = 0
  hasAudio.value = true
}

function stopNode() {
  if (raf) cancelAnimationFrame(raf)
  raf = 0
  if (src) {
    try {
      src.onended = null
      src.stop()
    } catch {
      /* 已结束则忽略 */
    }
    src = null
  }
}

function tick() {
  if (!playing.value || !src) return
  position.value = Math.min(segBase + (ctx!.currentTime - segStartAt) * rate.value, duration.value)
  if (position.value >= duration.value) {
    finishAudio()
    endedCb?.()
    return
  }
  raf = requestAnimationFrame(tick)
}

export function finishAudio() {
  playing.value = false
  stopNode()
}

export function playAudio() {
  if (!buffer) return
  const ac = ensureCtx()
  void ac.resume()
  if (position.value >= duration.value - 0.01) position.value = 0
  stopNode()
  src = ac.createBufferSource()
  src.buffer = buffer
  src.playbackRate.value = rate.value
  src.connect(ac.destination)
  segBase = position.value
  segStartAt = ac.currentTime
  src.start(0, segBase)
  playing.value = true
  raf = requestAnimationFrame(tick)
}

export function pauseAudio() {
  if (!playing.value) return
  if (src) {
    position.value = Math.min(
      segBase + (ctx!.currentTime - segStartAt) * rate.value,
      duration.value,
    )
  }
  finishAudio()
}

export function togglePlay() {
  if (playing.value) pauseAudio()
  else playAudio()
}

export function stopAudio() {
  finishAudio()
  position.value = 0
}

export function setRate(r: number) {
  rate.value = r
  if (src) src.playbackRate.value = r
}

/** 自然播完回调（用于触发 end 消息） */
export function onAudioEnded(cb: () => void) {
  endedCb = cb
}
