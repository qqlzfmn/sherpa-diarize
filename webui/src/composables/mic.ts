/**
 * 录音：getUserMedia → 16kHz 单声道 → 实时音频块回调 + 录音计时。
 */
import { ref } from 'vue'

export const micSeconds = ref(0)

let ctx: AudioContext | null = null
let stream: MediaStream | null = null
let proc: ScriptProcessorNode | null = null
let timer = 0

export async function startMic(onChunk: (f32: Float32Array) => void): Promise<void> {
  ctx = new AudioContext({ sampleRate: 16000 })
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })
  const source = ctx.createMediaStreamSource(stream)
  proc = ctx.createScriptProcessor(2048, 1, 1) // 128ms @16k
  proc.onaudioprocess = (e) => {
    const data = e.inputBuffer.getChannelData(0)
    onChunk(new Float32Array(data))
  }
  // 静音挂载，避免回放啸叫，同时保证处理器持续运行
  const mute = ctx.createGain()
  mute.gain.value = 0
  source.connect(proc)
  proc.connect(mute)
  mute.connect(ctx.destination)

  const t0 = performance.now()
  micSeconds.value = 0
  timer = window.setInterval(() => {
    micSeconds.value = (performance.now() - t0) / 1000
  }, 200)
}

export function stopMic() {
  if (timer) {
    clearInterval(timer)
    timer = 0
  }
  proc?.disconnect()
  proc = null
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
  if (ctx) {
    void ctx.close()
    ctx = null
  }
}
