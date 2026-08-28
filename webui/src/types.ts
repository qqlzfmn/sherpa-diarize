/** 后端 /api/models 返回结构 */
export interface ModelsInfo {
  models_ready: boolean
  asr_offline_ready: boolean
  asr_streaming_ready: boolean
  demo_wavs: Record<string, string>
}

/** ASR 模式 */
export type AsrMode = 'none' | 'offline' | 'streaming'

/** 一个说话人 turn 的最终结果 */
export interface TurnEvent {
  id: number
  start: number
  end: number
  speaker: number
  confidence: number
  text: string
}

/** 处理阶段 */
export type Phase =
  | 'idle' // 未开始
  | 'connecting' // 正在连接后端
  | 'ready' // 管线就绪，等待发送
  | 'streaming' // 处理中（发送/接收）
  | 'done' // 完成
  | 'error' // 错误

/** 已加载的音频片段（统一为 16kHz 单声道 Float32） */
export interface Clip {
  name: string
  duration: number
  /** 完整 16k 单声道采样 */
  samples: Float32Array
  /** 预切分的 250ms 块（每块 4000 采样，末块可能不足） */
  chunks: Float32Array[]
}

/** 播放倍速；0 表示"最快"（无声音、全速发送） */
export type PlayRate = 1 | 2 | 4 | 8 | 0

/** 音频源类型 */
export type SourceKind = 'demo' | 'upload' | 'record'

export const CHUNK_DUR = 0.25
export const SAMPLE_RATE = 16000
export const CHUNK_LEN = SAMPLE_RATE * CHUNK_DUR // 4000

/** 说话人调色板 */
export const SPEAKER_COLORS = [
  '#22d3ee', // 青
  '#fbbf24', // 琥珀
  '#f472b6', // 粉
  '#a78bfa', // 紫
  '#34d399', // 绿
  '#fb923c', // 橙
  '#60a5fa', // 蓝
  '#f87171', // 红
]

export function speakerColor(speaker: number): string {
  return SPEAKER_COLORS[Math.abs(speaker) % SPEAKER_COLORS.length]
}

/** 秒 → mm:ss 或 h:mm:ss */
export function fmtTime(sec: number): string {
  if (!isFinite(sec) || sec < 0) sec = 0
  const s = Math.floor(sec % 60)
  const m = Math.floor((sec / 60) % 60)
  const h = Math.floor(sec / 3600)
  const mm = String(m).padStart(2, '0')
  const ss = String(s).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`
}

/** 秒 → s 带一位小数（用于统计） */
export function fmtDur(sec: number): string {
  return `${sec.toFixed(1)}s`
}
