/** 音频工具：统一为 16kHz 单声道 Float32 音频块 */

export const TARGET_RATE = 16000
/** 发送块长：160ms = 2560 样本（后端建议 100–250ms） */
export const CHUNK = 2560

/** 混单声道 + 线性插值重采样到 16k */
export function toMono16k(buffer: AudioBuffer): Float32Array {
  const ch = buffer.numberOfChannels
  const len = buffer.length
  const mono = new Float32Array(len)
  for (let c = 0; c < ch; c++) {
    const data = buffer.getChannelData(c)
    for (let i = 0; i < len; i++) mono[i] += data[i] / ch
  }
  const srcRate = buffer.sampleRate
  if (srcRate === TARGET_RATE) return mono
  return resample(mono, srcRate, TARGET_RATE)
}

/** 线性插值重采样 */
export function resample(samples: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate) return samples
  const ratio = fromRate / toRate
  const outLen = Math.floor(samples.length / ratio)
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const pos = i * ratio
    const i0 = Math.floor(pos)
    const i1 = Math.min(i0 + 1, samples.length - 1)
    const f = pos - i0
    out[i] = samples[i0] * (1 - f) + samples[i1] * f
  }
  return out
}

/** 惰性解码上下文（Offline，不占用音频输出设备） */
let decodeCtx: OfflineAudioContext | null = null
export function decodeAudio(ab: ArrayBuffer): Promise<AudioBuffer> {
  if (!decodeCtx) decodeCtx = new OfflineAudioContext(1, 1, TARGET_RATE)
  return decodeCtx.decodeAudioData(ab)
}
