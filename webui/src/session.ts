import type { AsrMode } from './types'
import * as storeApi from './store'

/* ------------------------------------------------------------------ */
/* WebSocket 会话：连接 → config → 二进制音频流 → end/stop              */
/* ------------------------------------------------------------------ */

type WsIncoming =
  | { type: 'started'; asr_mode: string }
  | { type: 'partial'; text: string }
  | { type: 'event'; start: number; end: number; speaker: number; confidence: number; text: string }
  | { type: 'progress'; t: number }
  | { type: 'done'; speakers: number }
  | { type: 'error'; message: string }

export class Session {
  private ws: WebSocket | null = null
  private startedResolve: (() => void) | null = null
  private startedReject: ((e: Error) => void) | null = null
  /** 会话是否仍可发送（收到 started 且未结束） */
  private sendable = false
  private closed = false
  /** 客户端主动调用过 end/stop */
  private finalized = false

  /** 建立连接、发送 config、等待 started */
  open(asrMode: AsrMode): Promise<void> {
    const { promise, resolve, reject } = Promise.withResolvers<void>()
    storeApi.setPhase('connecting')
    storeApi.setError(null)
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${location.host}/ws`)
    this.ws = ws
    this.closed = false
    this.finalized = false
    this.startedResolve = resolve
    this.startedReject = reject

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'config', asr_mode: asrMode }))
    }
    ws.onerror = () => {
      if (!this.closed) {
        const e = new Error('无法连接后端服务，请确认服务已启动')
        this.startedReject?.(e)
        this.startedReject = null
      }
    }
    ws.onclose = () => {
      this.sendable = false
      if (!this.closed && this.startedReject) {
        const e = new Error('连接已断开')
        this.startedReject(e)
        this.startedReject = null
      } else if (!this.closed && storeApi.store.phase !== 'done') {
        storeApi.setPhase('error')
        storeApi.setError('连接已断开')
      }
      this.closed = true
    }
    ws.onmessage = (ev: MessageEvent) => this.handle(ev)
    return promise
  }

  private handle(ev: MessageEvent): void {
    let msg: WsIncoming
    try {
      msg = JSON.parse(String(ev.data)) as WsIncoming
    } catch {
      return // 忽略非 JSON 消息
    }
    switch (msg.type) {
      case 'started':
        this.sendable = true
        storeApi.setPhase('ready')
        this.startedResolve?.()
        this.startedResolve = null
        this.startedReject = null
        break
      case 'partial':
        if (storeApi.store.phase === 'streaming' || storeApi.store.phase === 'ready') {
          storeApi.setPartial(msg.text)
        }
        break
      case 'event':
        if (storeApi.store.phase === 'streaming' || storeApi.store.phase === 'ready') {
          storeApi.pushEvent({
            start: msg.start,
            end: msg.end,
            speaker: msg.speaker,
            confidence: msg.confidence,
            text: msg.text,
          })
        }
        break
      case 'progress':
        storeApi.setProgress(msg.t)
        break
      case 'done':
        storeApi.setPartial(null)
        storeApi.setPhase('done')
        storeApi.store.lastSpeakers = msg.speakers
        break
      case 'error':
        storeApi.setPhase('error')
        storeApi.setError(msg.message)
        break
    }
  }

  /** 发送一块 16k Float32 音频（250ms） */
  sendChunk(chunk: Float32Array): void {
    if (!this.sendable || !this.ws || this.ws.readyState !== WebSocket.OPEN) return
    this.ws.send(chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength))
  }

  /** 音频流结束 */
  end(): void {
    if (this.finalized) return
    this.finalized = true
    this.sendable = false
    this.ws?.send(JSON.stringify({ type: 'end' }))
  }

  /** 中断处理 */
  stop(): void {
    if (this.finalized) return
    this.finalized = true
    this.sendable = false
    try {
      this.ws?.send(JSON.stringify({ type: 'stop' }))
    } catch {
      /* 忽略 */
    }
  }

  close(): void {
    this.closed = true
    this.sendable = false
    this.finalized = true
    try {
      this.ws?.close()
    } catch {
      /* 忽略 */
    }
    this.ws = null
  }
}
