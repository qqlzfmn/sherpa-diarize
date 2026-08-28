/** 产品域类型 —— 与后端契约一一对应 */

export type AsrMode = 'none' | 'offline' | 'streaming'

export type Phase = 'idle' | 'connecting' | 'processing' | 'done' | 'error'

export type SourceKind = 'demo' | 'upload' | 'mic'

/** 一个说话人 turn 的最终结果 */
export interface Turn {
  id: number
  start: number
  end: number
  speaker: number
  confidence: number
  text: string
}

/** GET /api/models 响应 */
export interface ModelsInfo {
  models_ready: boolean
  asr_offline_ready: boolean
  asr_streaming_ready: boolean
  demo_wavs: Record<string, string>
}

/** 服务端 → 客户端 WS 文本消息（顺序到达） */
export type ServerMessage =
  | { type: 'started'; asr_mode: AsrMode }
  | { type: 'partial'; text: string }
  | {
      type: 'event'
      start: number
      end: number
      speaker: number
      confidence: number
      text: string
    }
  | { type: 'progress'; t: number }
  | { type: 'done'; speakers: number }
  | { type: 'error'; message: string }

export const MODE_LABELS: Record<AsrMode, string> = {
  none: '无 ASR',
  offline: '离线转写',
  streaming: '流式转写',
}
