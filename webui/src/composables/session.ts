/**
 * 会话核心：WebSocket 生命周期 + 后端消息解析 + 共享响应式状态。
 * 单例 —— 所有组件直接消费同一个 session 对象。
 */
import { reactive } from 'vue'
import type { AsrMode, ModelsInfo, Phase, ServerMessage, SourceKind, Turn } from '../types'
import { t } from './i18n'

export const session = reactive({
  phase: 'idle' as Phase,
  wsConnected: false,
  asrMode: 'streaming' as AsrMode,
  sourceKind: null as SourceKind | null,
  sourceName: '',
  turns: [] as Turn[],
  /** 流式识别中的"未定型"预览文本 */
  partial: null as string | null,
  /** 已处理音频秒数 */
  progress: 0,
  speakersTotal: 0,
  error: null as string | null,
  startedAt: 0,
  endedAt: 0,
  models: null as ModelsInfo | null,
})

let ws: WebSocket | null = null
let turnId = 1
let settle: { ok: () => void; fail: (e: Error) => void } | null = null
let intentionalClose = false

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

function failSession(e: Error) {
  session.error = e.message
  session.partial = null
  session.phase = 'error'
}

function handleMessage(raw: string) {
  let msg: ServerMessage
  try {
    msg = JSON.parse(raw) as ServerMessage
  } catch {
    return
  }
  switch (msg.type) {
    case 'started':
      session.wsConnected = true
      session.phase = 'processing'
      session.startedAt = Date.now()
      settle?.ok()
      settle = null
      break
    case 'partial':
      // 仅在处理中接受预览；结束后的残留 partial 由 done 清空
      if (session.phase === 'processing') session.partial = msg.text
      break
    case 'event':
      session.turns.push({
        id: turnId++,
        start: msg.start,
        end: msg.end,
        speaker: msg.speaker,
        confidence: msg.confidence,
        text: msg.text,
      })
      break
    case 'progress':
      session.progress = msg.t
      break
    case 'done':
      session.speakersTotal = msg.speakers
      session.partial = null
      session.phase = 'done'
      session.endedAt = Date.now()
      break
    case 'error':
      session.partial = null
      session.phase = 'error'
      session.error = msg.message
      settle?.fail(new Error(msg.message))
      settle = null
      break
  }
}

export async function fetchModels(): Promise<ModelsInfo> {
  const res = await fetch('/api/models')
  if (!res.ok) throw new Error(t('session.modelsFail', { status: res.status }))
  const data = (await res.json()) as ModelsInfo
  session.models = data
  return data
}

/** 建立连接、发送 config、等待 started；失败抛出 Error。 */
export function begin(mode: AsrMode, kind: SourceKind, name: string): Promise<void> {
  reset()
  session.phase = 'connecting'
  session.asrMode = mode
  session.sourceKind = kind
  session.sourceName = name
  session.error = null

  return new Promise<void>((resolve, reject) => {
    let socket: WebSocket
    try {
      socket = new WebSocket(wsUrl())
    } catch (e) {
      failSession(e instanceof Error ? e : new Error(t('session.wsCreate')))
      reject(e instanceof Error ? e : new Error(t('session.wsCreate')))
      return
    }
    ws = socket
    socket.binaryType = 'arraybuffer'
    intentionalClose = false

    const timeout = window.setTimeout(() => {
      if (!settle) return
      const f = settle.fail
      settle = null
      closeWs()
      f(new Error(t('session.wsTimeout')))
    }, 20000)

    settle = {
      ok: () => {
        window.clearTimeout(timeout)
        resolve()
      },
      fail: (e) => {
        window.clearTimeout(timeout)
        failSession(e)
        reject(e)
      },
    }

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: 'config', asr_mode: mode }))
    }
    socket.onmessage = (ev) => {
      if (typeof ev.data === 'string') handleMessage(ev.data)
    }
    socket.onerror = () => {
      if (settle) {
        const f = settle.fail
        settle = null
        f(new Error(t('session.wsConnectFail')))
      }
    }
    socket.onclose = () => {
      session.wsConnected = false
      if (intentionalClose) return
      if (settle) {
        const f = settle.fail
        settle = null
        f(new Error(t('session.wsClosed')))
      } else if (session.phase === 'processing') {
        failSession(new Error(t('session.wsBroken')))
      }
    }
  })
}

export function sendChunk(f32: Float32Array) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(f32)
}

export function sendEnd() {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'end' }))
}

export function sendStop() {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
}

/** 主动关闭连接（发送 done/stop 之后） */
export function closeWs() {
  intentionalClose = true
  if (ws) {
    ws.onclose = null
    try {
      ws.close()
    } catch {
      /* 忽略 */
    }
  }
  ws = null
}

/** 完全复位到初始态 */
export function reset() {
  closeWs()
  session.phase = 'idle'
  session.wsConnected = false
  session.turns = []
  session.partial = null
  session.progress = 0
  session.speakersTotal = 0
  session.error = null
  session.startedAt = 0
  session.endedAt = 0
  session.sourceKind = null
  session.sourceName = ''
}
