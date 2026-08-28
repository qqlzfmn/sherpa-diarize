<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { session } from '../composables/session'
import { playing, position, duration as playDuration } from '../composables/playback'
import type { Turn } from '../types'
import { fmtClock, fmtStamp } from '../utils/time'
import { hexA, speakerColor, speakerLabel } from '../utils/speaker'

const props = defineProps<{ waveform: Float32Array | null }>()

/** 像素 / 秒 —— 光谱带比例 */
const PPS = 46
const PAD = 14

const scrollEl = ref<HTMLElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const rootEl = ref<HTMLElement | null>(null)
const follow = ref(true)
const hover = ref<{ turn: Turn; x: number; y: number } | null>(null)

const totalDur = computed(() =>
  Math.max(session.progress, playDuration.value, ...session.turns.map((t) => t.end), 0),
)
const contentW = computed(() => Math.max(PAD * 2 + totalDur.value * PPS, 900))

/** 游标：播放中随播放位置，处理中暂停时随已处理进度，完成后随回放 */
const cursorSeconds = computed(() => {
  if (playing.value) return position.value
  if (session.phase === 'processing') return session.progress
  if (session.phase === 'done') return position.value
  return 0
})
const cursorX = computed(() => PAD + cursorSeconds.value * PPS)

const segStyle = (t: Turn) => {
  const color = speakerColor(t.speaker)
  return {
    left: `${PAD + t.start * PPS}px`,
    width: `${Math.max((t.end - t.start) * PPS, 7)}px`,
    background: `linear-gradient(180deg, ${hexA(color, 0.22)}, ${hexA(color, 0.12)})`,
    borderLeftColor: color,
    opacity: t.text ? 1 : 0.55,
  }
}

const ticks = computed(() => {
  const n = Math.ceil(totalDur.value)
  const out: { pos: number; label: string | null }[] = []
  for (let i = 0; i <= n; i++) {
    out.push({ pos: PAD + i * PPS, label: i % 5 === 0 ? fmtClock(i) : null })
  }
  return out
})

/* ---------- 波形（一次绘制，像素级 min/max 下采样） ---------- */
function drawWave() {
  const canvas = canvasEl.value
  const wave = props.waveform
  if (!canvas || !wave || wave.length === 0) return
  const dpr = window.devicePixelRatio || 1
  const w = contentW.value
  const h = 74
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  const g = canvas.getContext('2d')
  if (!g) return
  g.scale(dpr, dpr)
  const spp = wave.length / w // samples per pixel column
  const mid = h / 2
  g.strokeStyle = 'rgba(150, 170, 210, 0.16)'
  g.lineWidth = 1
  g.beginPath()
  for (let x = 0; x < w; x++) {
    const i0 = Math.floor(x * spp)
    const i1 = Math.min(Math.floor((x + 1) * spp), wave.length - 1)
    let mn = 1
    let mx = -1
    for (let i = i0; i <= i1; i++) {
      const v = wave[i]
      if (v < mn) mn = v
      if (v > mx) mx = v
    }
    const y0 = mid + mx * (h / 2 - 4)
    const y1 = mid + mn * (h / 2 - 4)
    g.moveTo(x + 0.5, y0)
    g.lineTo(x + 0.5, y1)
  }
  g.stroke()
}

function onSegMove(t: Turn, ev: MouseEvent) {
  const rect = rootEl.value?.getBoundingClientRect()
  if (!rect) return
  const x = Math.min(Math.max(ev.clientX - rect.left + 16, 8), rect.width - 264)
  const y = Math.max(ev.clientY - rect.top - 96, 44)
  hover.value = { turn: t, x, y }
}
function onSegLeave() {
  hover.value = null
}

/* ---------- 自动跟随 ---------- */
function followCursor() {
  const el = scrollEl.value
  if (!el || !follow.value) return
  const x = cursorX.value
  const lo = el.scrollLeft + 70
  const hi = el.scrollLeft + el.clientWidth - 70
  if (x < lo || x > hi) el.scrollLeft = Math.max(0, x - el.clientWidth / 2)
}

let followRaf = 0
function rafFollow() {
  cancelAnimationFrame(followRaf)
  followRaf = requestAnimationFrame(() => {
    followCursor()
    if (session.phase === 'processing' || playing.value) rafFollow()
  })
}

watch(
  () => [session.progress, position.value, session.turns.length],
  async () => {
    await nextTick()
    followCursor()
  },
)
watch(contentW, () => drawWave())

onMounted(() => {
  rafFollow()
  drawWave()
  window.addEventListener('resize', drawWave)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(followRaf)
  window.removeEventListener('resize', drawWave)
})
</script>

<template>
  <section ref="rootEl" class="timeline panel">
    <div class="t-head">
      <h2 class="panel-title">说话人时间轴</h2>
      <span class="hint">悬停分段查看详情</span>
      <div class="t-right">
        <span v-if="session.phase === 'processing'" class="live-tag">
          <i class="pulse-dot" />实时处理中 · 已处理 {{ fmtClock(session.progress) }}
        </span>
        <label class="follow" :class="{ on: follow }">
          <input v-model="follow" type="checkbox" />
          <span class="box" />自动跟随
        </label>
      </div>
    </div>

    <div ref="scrollEl" class="t-scroll">
      <div class="t-inner" :style="{ width: contentW + 'px' }">
        <!-- 刻度 -->
        <div class="ruler">
          <template v-for="(t, i) in ticks" :key="i">
            <span class="tick" :class="{ major: t.label }" :style="{ left: t.pos + 'px' }" />
            <span v-if="t.label" class="tick-label mono" :style="{ left: t.pos + 'px' }">
              {{ t.label }}
            </span>
          </template>
        </div>

        <!-- 光谱带 -->
        <div class="lane">
          <canvas ref="canvasEl" class="wave" />
          <div class="seg" v-for="t in session.turns" :key="t.id" :style="segStyle(t)"
            @mousemove="onSegMove(t, $event)" @mouseleave="onSegLeave">
            <span class="seg-chip" :style="{ color: speakerColor(t.speaker), borderColor: hexA(speakerColor(t.speaker), 0.5) }">
              {{ speakerLabel(t.speaker) }}
            </span>
            <span v-if="!t.text" class="seg-empty">（无语音）</span>
          </div>

          <div v-if="!session.turns.length" class="lane-empty">
            <span v-if="session.phase === 'processing'">正在分光识别…首个分段出现后将在此着色</span>
            <span v-else>尚无分段 — 选择音频并开始处理后，说话人色带将出现在这里</span>
          </div>

          <!-- 游标 -->
          <div class="cursor" :style="{ left: cursorX + 'px' }">
            <i class="head" />
            <i class="line" />
          </div>
        </div>
      </div>
    </div>

    <!-- hover 详情 -->
    <div v-if="hover" class="tip" :style="{ left: hover.x + 'px', top: hover.y + 'px' }">
      <div class="tip-row">
        <span class="tip-speaker" :style="{ color: speakerColor(hover.turn.speaker) }">
          {{ speakerLabel(hover.turn.speaker) }}
        </span>
        <span class="tip-time mono">{{ fmtStamp(hover.turn.start) }} – {{ fmtStamp(hover.turn.end) }}</span>
        <span class="tip-conf mono">置信 {{ Math.round(hover.turn.confidence * 100) }}%</span>
      </div>
      <p class="tip-text">{{ hover.turn.text || '（无语音内容）' }}</p>
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: var(--bg-1);
  border: 1px solid var(--line-1);
  border-radius: var(--radius);
}
.timeline {
  display: flex;
  flex-direction: column;
  padding: 10px 14px 12px;
  gap: 8px;
  flex-shrink: 0;
}
.t-head {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 20px;
}
.panel-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--ink-mid);
}
.hint {
  font-size: 11.5px;
  color: var(--ink-low);
}
.t-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 14px;
}
.live-tag {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  color: var(--good);
}
.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--good);
  animation: pulse 1.1s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
.follow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--ink-low);
  cursor: pointer;
  user-select: none;
}
.follow.on {
  color: var(--ink-mid);
}
.follow input {
  display: none;
}
.box {
  width: 13px;
  height: 13px;
  border-radius: 4px;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s var(--ease);
}
.follow.on .box {
  background: var(--accent);
  border-color: var(--accent);
}
.follow.on .box::after {
  content: '';
  width: 5px;
  height: 3px;
  border-left: 1.6px solid #071018;
  border-bottom: 1.6px solid #071018;
  transform: rotate(-45deg) translateY(-1px);
}

.t-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  border-radius: var(--radius-sm);
}
.t-inner {
  position: relative;
  min-width: 100%;
  padding-bottom: 4px;
}
.ruler {
  position: relative;
  height: 22px;
}
.tick {
  position: absolute;
  top: 2px;
  bottom: 6px;
  width: 1px;
  background: var(--line-1);
}
.tick.major {
  background: var(--line-2);
}
.tick-label {
  position: absolute;
  top: 7px;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--ink-low);
  pointer-events: none;
}
.lane {
  position: relative;
  height: 74px;
  border-top: 1px solid var(--line-1);
  border-bottom: 1px solid var(--line-1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.012), transparent);
}
.wave {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.seg {
  position: absolute;
  top: 6px;
  bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border-left: 3px solid;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: filter 0.15s var(--ease);
}
.seg:hover {
  filter: brightness(1.25);
}
.seg-chip {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  padding: 1px 7px;
  border-radius: 99px;
  border: 1px solid;
  background: rgba(7, 9, 13, 0.55);
}
.seg-empty {
  font-size: 10.5px;
  color: var(--ink-low);
  white-space: nowrap;
}
.lane-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12.5px;
  color: var(--ink-low);
  letter-spacing: 0.03em;
  pointer-events: none;
}
.cursor {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  pointer-events: none;
  z-index: 5;
}
.head {
  position: absolute;
  top: -3px;
  left: -5px;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 7px solid var(--ink-hi);
  filter: drop-shadow(0 0 4px rgba(233, 238, 248, 0.7));
}
.line {
  position: absolute;
  top: 4px;
  bottom: 0;
  left: 0;
  width: 2px;
  background: var(--ink-hi);
  box-shadow: 0 0 10px rgba(233, 238, 248, 0.55);
}

.tip {
  position: absolute;
  z-index: 40;
  width: 248px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--bg-3);
  border: 1px solid var(--line-2);
  box-shadow: var(--shadow);
  pointer-events: none;
}
.tip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.tip-speaker {
  font-size: 12px;
  font-weight: 700;
}
.tip-time {
  font-size: 11px;
  color: var(--ink-mid);
}
.tip-conf {
  font-size: 11px;
  color: var(--ink-low);
}
.tip-text {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-hi);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
