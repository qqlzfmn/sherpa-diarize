import { fetchModels, fetchDemoWav, decodeTo16kMono, makeClip, startRecording } from './audio'
import { Session } from './session'
import { player } from './player'
import * as s from './store'
import type { AsrMode, PlayRate } from './types'

/* ------------------------------------------------------------------ */
/* 模型 / 音频源加载                                                   */
/* ------------------------------------------------------------------ */

export async function loadModels(): Promise<void> {
  try {
    const m = await fetchModels()
    s.setModels(m)
  } catch (err) {
    s.setModelsError(err instanceof Error ? err.message : String(err))
  }
}

export async function loadDemoWav(name: string, url: string): Promise<void> {
  s.setClipLoading(true)
  s.setClipError(null)
  try {
    const data = await fetchDemoWav(url)
    const samples = await decodeTo16kMono(data)
    s.setClip(makeClip(samples, name))
  } catch (err) {
    s.setClipError(err instanceof Error ? err.message : String(err))
  } finally {
    s.setClipLoading(false)
  }
}

export async function loadUploadFile(file: File): Promise<void> {
  s.setClipLoading(true)
  s.setClipError(null)
  try {
    const data = await file.arrayBuffer()
    const samples = await decodeTo16kMono(data)
    s.setClip(makeClip(samples, file.name))
  } catch (err) {
    s.setClipError(`音频解码失败：${err instanceof Error ? err.message : String(err)}`)
  } finally {
    s.setClipLoading(false)
  }
}

/* ------------------------------------------------------------------ */
/* 录音                                                               */
/* ------------------------------------------------------------------ */

let stopRecorder: (() => void) | null = null
let recTotalSamples = 0

export async function startRec(): Promise<void> {
  if (s.store.isRecording) return
  s.store.isRecording = true
  s.store.recordDuration = 0
  recTotalSamples = 0
  stopRecorder = await startRecording(
    (chunk) => {
      recTotalSamples += chunk.length
      s.store.recordDuration = recTotalSamples / 16000
    },
    (samples, dur) => {
      s.store.isRecording = false
      s.store.recordDuration = dur
      if (samples.length > 0) {
        s.setClip(makeClip(samples, '录音片段'))
      } else {
        s.setClipError('录音内容为空')
      }
    },
    (msg) => {
      s.store.isRecording = false
      s.setClipError(`录音失败：${msg}`)
    },
  )
}

export function stopRec(): void {
  stopRecorder?.()
  stopRecorder = null
}

/* ------------------------------------------------------------------ */
/* 处理会话                                                           */
/* ------------------------------------------------------------------ */

let session: Session | null = null

export function getSession(): Session | null {
  return session
}

/** 开始处理：连接后端 → 发送音频块（与播放同步） */
export async function startProcessing(): Promise<void> {
  const clip = s.store.clip
  const phase = s.store.phase
  if (!clip || phase === 'streaming' || phase === 'connecting' || phase === 'ready') return
  if (s.store.isRecording) return

  s.resetSession()
  const ses = new Session()
  session = ses
  player.bind(ses, clip, s.store.rate)
  try {
    await ses.open(s.store.asrMode) // connecting → ready（收到 started）
    s.setPhase('streaming')
    await player.start()
  } catch (err) {
    ses.close()
    player.destroy()
    session = null
    s.setPhase('error')
    s.setError(err instanceof Error ? err.message : String(err))
  }
}

/** 暂停/继续播放（发送随之暂停/继续） */
export function togglePlay(): void {
  if (s.store.playing) {
    player.pause()
    s.setPlaying(false)
  } else {
    player.resume()
    s.setPlaying(true)
  }
}

/** 修改倍速 */
export function changeRate(rate: PlayRate): void {
  player.setRate(rate)
}

/** 中断处理（保留已得结果） */
export function stopProcessing(): void {
  player.destroy()
  session?.stop()
  session?.close()
  session = null
  s.setPhase('done')
}

export function setAsrMode(mode: AsrMode): void {
  s.store.asrMode = mode
}
