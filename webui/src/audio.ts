import type { Clip, ModelsInfo } from './types'
import { CHUNK_LEN, SAMPLE_RATE } from './types'

/* ------------------------------------------------------------------ */
/* HTTP API                                                            */
/* ------------------------------------------------------------------ */

export async function fetchModels(): Promise<ModelsInfo> {
  const res = await fetch('/api/models')
  if (!res.ok) throw new Error(`后端接口异常（HTTP ${res.status}）`)
  return (await res.json()) as ModelsInfo
}

export async function fetchDemoWav(url: string): Promise<ArrayBuffer> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`示例音频加载失败（HTTP ${res.status}）`)
  return await res.arrayBuffer()
}

/* ------------------------------------------------------------------ */
/* 音频解码 / 混单声道 / 重采样到 16kHz                                 */
/* ------------------------------------------------------------------ */

/** 线性插值重采样（整段） */
function resampleBuffer(input: Float32Array, fromRate: number): Float32Array {
  if (fromRate === SAMPLE_RATE) return input
  const ratio = fromRate / SAMPLE_RATE
  const outLen = Math.max(1, Math.floor(input.length / ratio))
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const pos = i * ratio
    const i0 = Math.floor(pos)
    const i1 = Math.min(i0 + 1, input.length - 1)
    const f = pos - i0
    out[i] = input[i0] + (input[i1] - input[i0]) * f
  }
  return out
}

function mixToMono(buf: AudioBuffer): Float32Array {
  const chs = buf.numberOfChannels
  const n = buf.length
  const out = new Float32Array(n)
  if (chs === 1) {
    out.set(buf.getChannelData(0))
    return out
  }
  for (let c = 0; c < chs; c++) {
    const d = buf.getChannelData(c)
    for (let i = 0; i < n; i++) out[i] += d[i]
  }
  for (let i = 0; i < n; i++) out[i] /= chs
  return out
}

/** 将任意 AudioBuffer 解码为 16kHz 单声道采样 */
export function bufferTo16kMono(buf: AudioBuffer): Float32Array {
  return resampleBuffer(mixToMono(buf), buf.sampleRate)
}

/** 获取 AudioContext 构造器（兼容 Safari webkit 前缀） */
export function getAudioContextCtor(): typeof AudioContext {
  if (typeof AudioContext !== 'undefined') return AudioContext
  const w: unknown = window
  if (w && typeof w === 'object' && 'webkitAudioContext' in w) {
    return (w as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  }
  throw new Error('当前浏览器不支持 Web Audio API')
}

/** 解码 ArrayBuffer（wav/mp3/ogg…）→ 16k 单声道采样 */
export async function decodeTo16kMono(data: ArrayBuffer): Promise<Float32Array> {
  const ctx = new (getAudioContextCtor())()
  try {
    const buf = await ctx.decodeAudioData(data.slice(0))
    return bufferTo16kMono(buf)
  } finally {
    void ctx.close()
  }
}

/** 16k 单声道采样 → Clip（预切 250ms 块） */
export function makeClip(samples: Float32Array, name: string): Clip {
  const chunks: Float32Array[] = []
  for (let off = 0; off < samples.length; off += CHUNK_LEN) {
    chunks.push(samples.subarray(off, off + CHUNK_LEN))
  }
  if (chunks.length === 0) chunks.push(new Float32Array(0))
  return {
    name,
    duration: samples.length / SAMPLE_RATE,
    samples,
    chunks,
  }
}

/* ------------------------------------------------------------------ */
/* 录音：getUserMedia → 16kHz 单声道                                    */
/* ------------------------------------------------------------------ */

/**
 * 流式重采样器：把任意采样率的分块输入转成 16kHz 输出，
 * 跨块插值（记录上一块末采样与小数相位）。
 */
class StreamingResampler {
  private ratio = 1
  private frac = 0
  private prev = 0

  reset(fromRate: number): void {
    this.ratio = fromRate / SAMPLE_RATE
    this.frac = 0
    this.prev = 0
  }

  /** 输入一块音频，返回重采样后的 16k 数据（长度 ≈ 输入/ratio） */
  process(input: Float32Array): Float32Array {
    const outLen = Math.max(0, Math.floor(input.length / this.ratio))
    const out = new Float32Array(outLen)
    for (let i = 0; i < outLen; i++) {
      const pos = this.frac + i * this.ratio
      const i0 = Math.floor(pos)
      const i1 = Math.min(i0 + 1, input.length - 1)
      const f = pos - i0
      const a = i0 >= 0 ? input[i0] : this.prev
      out[i] = a + (input[i1] - a) * f
    }
    this.frac = this.frac + outLen * this.ratio - input.length
    this.prev = input[input.length - 1] ?? 0
    return out
  }
}

/**
 * 启动录音。优先请求 16kHz 采样率；若浏览器未满足
 * （如 Safari 忽略 sampleRate），在 ScriptProcessor 内重采样到 16k。
 *
 * @param onChunk    每块 16k 数据到达时回调（仅作时长/电平反馈）
 * @param onDone     停止录音后回调 (16k 单声道采样, 时长秒)
 * @param onError    录音启动失败
 * @returns 停止函数（幂等）
 */
export async function startRecording(
  onChunk: (chunk: Float32Array) => void,
  onDone: (samples: Float32Array, durationSec: number) => void,
  onError: (msg: string) => void,
): Promise<() => void> {
  let ctx: AudioContext | null = null
  let stream: MediaStream | null = null
  let processor: ScriptProcessorNode | null = null
  let source: MediaStreamAudioSourceNode | null = null
  const resampler = new StreamingResampler()
  const collected: Float32Array[] = []
  let total = 0
  let stopped = false

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
    })
    ctx = new (getAudioContextCtor())({ sampleRate: SAMPLE_RATE })
    resampler.reset(ctx.sampleRate)
    source = ctx.createMediaStreamSource(stream)
    processor = ctx.createScriptProcessor(4096, 1, 1)
    const sink = ctx.createGain()
    sink.gain.value = 0 // 不输出麦克风回放
    processor.onaudioprocess = (e: AudioProcessingEvent) => {
      if (stopped) return
      const input = e.inputBuffer.getChannelData(0)
      const chunk =
        ctx!.sampleRate === SAMPLE_RATE ? input.slice(0) : resampler.process(input)
      collected.push(chunk)
      total += chunk.length
      onChunk(chunk)
    }
    source.connect(processor)
    processor.connect(sink)
    sink.connect(ctx.destination)

    return () => {
      if (stopped) return
      stopped = true
      try {
        source?.disconnect()
        processor?.disconnect()
        stream?.getTracks().forEach((t) => t.stop())
        void ctx?.close()
      } catch {
        /* 关闭阶段忽略 */
      }
      const samples = new Float32Array(total)
      let off = 0
      for (const c of collected) {
        samples.set(c, off)
        off += c.length
      }
      onDone(samples, total / SAMPLE_RATE)
    }
  } catch (err) {
    onError(err instanceof Error ? err.message : String(err))
    return () => undefined
  }
}
