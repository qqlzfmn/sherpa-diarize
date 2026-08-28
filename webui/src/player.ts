import type { Clip, PlayRate } from './types'
import { CHUNK_DUR } from './types'
import { getAudioContextCtor } from './audio'
import type { Session } from './session'
import * as storeApi from './store'

/* ------------------------------------------------------------------ */
/* 播放引擎：把 Clip 逐块发送给后端，发送节奏与播放同步                 */
/*                                                                     */
/* - 正常倍速：AudioContext + AudioBufferSourceNode 播放，              */
/*   用音频时钟计算已播放时长，逐块发送（倍速同时加快发送）。            */
/*   暂停用 ctx.suspend()——音频时钟冻结，发送自然停顿。                 */
/* - 最快（turbo）：不发声，按定时器以最高速度泵出所有分块。            */
/* ------------------------------------------------------------------ */

export class Player {
  private session: Session | null = null
  private clip: Clip | null = null

  private ctx: AudioContext | null = null
  private src: AudioBufferSourceNode | null = null
  private startCtxTime = 0
  private lastRateAt = 0
  private accum = 0
  private rate = 1
  private sentIdx = 0
  private rafId = 0
  private turboTimer = 0
  private ended = false

  /** 绑定会话（每次开始处理前设置） */
  bind(session: Session, clip: Clip, rate: PlayRate): void {
    this.session = session
    this.clip = clip
    this.rate = rate === 0 ? 1 : rate
    this.sentIdx = 0
    this.accum = 0
    this.ended = false
  }

  /** 开始播放+发送 */
  async start(): Promise<void> {
    const clip = this.clip
    const session = this.session
    if (!clip || !session) return
    storeApi.setPos(0)
    storeApi.setPlaying(true)
    storeApi.setTurbo(this.rate === 0)

    if (this.rate === 0) {
      // ---- 最快模式：无声音，全速发送 ----
      this.turboTimer = window.setInterval(() => this.turboTick(), 12)
      return
    }
    this.startAudio(clip)
    this.loop()
  }

  private startAudio(clip: Clip): void {
    this.ctx = new (getAudioContextCtor())()
    const buffer = this.ctx.createBuffer(1, clip.samples.length, 16000)
    buffer.copyToChannel(clip.samples, 0)
    const src = this.ctx.createBufferSource()
    src.buffer = buffer
    src.playbackRate.value = this.rate
    src.connect(this.ctx.destination)
    this.src = src
    this.startCtxTime = this.ctx.currentTime + 0.12
    this.lastRateAt = this.startCtxTime
    src.onended = () => {
      if (!this.ended) {
        this.ended = true
        storeApi.setPos(clip.duration)
        this.finishStream()
      }
    }
    src.start(this.startCtxTime)
  }

  private playedDur(): number {
    const clip = this.clip
    const ctx = this.ctx
    const src = this.src
    if (!clip || !ctx || !src) return 0
    const now = ctx.currentTime
    return Math.min(this.accum + (now - this.lastRateAt) * this.rate, clip.duration)
  }

  /** 修改倍速（播放中） */
  setRate(rate: PlayRate): void {
    if (this.rate === 0 && rate === 0) return
    if ((this.rate === 0) !== (rate === 0)) {
      // 最快 ↔ 有声倍速：需重启播放通道
      this.stopTurbo()
      this.disposeAudio()
      const clip = this.clip
      const session = this.session
      storeApi.setRate(rate)
      storeApi.setTurbo(rate === 0)
      if (!clip || !session) {
        // 尚未开始处理：仅记录倍速
        this.rate = rate === 0 ? 1 : rate
        return
      }
      const pos = storeApi.store.pos
      this.rate = rate === 0 ? 1 : rate
      this.accum = pos
      this.sentIdx = Math.floor(pos / CHUNK_DUR)
      if (rate === 0) {
        this.turboTimer = window.setInterval(() => this.turboTick(), 12)
      } else {
        this.startAudio(clip)
        this.loop()
      }
      return
    }
    // 有声倍速之间切换：用累积时长修正
    if (this.src && this.ctx) {
      const now = this.ctx.currentTime
      this.accum += (now - this.lastRateAt) * this.rate
      this.lastRateAt = now
    }
    this.rate = rate
    if (this.src) this.src.playbackRate.value = rate
    storeApi.setRate(rate)
    storeApi.setTurbo(false)
  }

  private stopTurbo(): void {
    if (this.turboTimer !== 0) {
      window.clearInterval(this.turboTimer)
      this.turboTimer = 0
    }
  }

  private turboTick(): void {
    const clip = this.clip
    const session = this.session
    if (!clip || !session) return
    if (this.sentIdx >= clip.chunks.length) {
      this.stopTurbo()
      storeApi.setPos(clip.duration)
      this.finishStream()
      return
    }
    session.sendChunk(clip.chunks[this.sentIdx])
    this.sentIdx++
    storeApi.setPos(this.sentIdx * CHUNK_DUR)
  }

  private loop(): void {
    const clip = this.clip
    const session = this.session
    if (!clip || !session) return
    if (this.ended) return
    const dur = this.playedDur()
    const target = Math.min(clip.chunks.length, Math.floor(dur / CHUNK_DUR))
    while (this.sentIdx < target) {
      session.sendChunk(clip.chunks[this.sentIdx])
      this.sentIdx++
    }
    storeApi.setPos(dur)
    if (this.sentIdx >= clip.chunks.length) {
      if (!this.ended) {
        this.ended = true
        this.finishStream()
      }
      return
    }
    this.rafId = requestAnimationFrame(() => this.loop())
  }

  /** 音频发完 → 发送 end */
  private finishStream(): void {
    this.session?.end()
    this.disposeAudio()
  }

  private disposeAudio(): void {
    if (this.rafId !== 0) {
      cancelAnimationFrame(this.rafId)
      this.rafId = 0
    }
    try {
      this.src?.stop()
    } catch {
      /* 已停止 */
    }
    this.src?.disconnect()
    this.src = null
    void this.ctx?.close()
    this.ctx = null
  }

  pause(): void {
    if (this.rate === 0) return // 最快模式不可暂停
    void this.ctx?.suspend()
  }

  resume(): void {
    if (this.rate === 0) return
    void this.ctx?.resume()
  }

  /** 终止（停止/出错时）：停止一切发送与播放 */
  destroy(): void {
    this.stopTurbo()
    this.disposeAudio()
    this.session = null
    this.clip = null
    storeApi.setPlaying(false)
  }
}

export const player = new Player()
