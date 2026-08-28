<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { store, speakerStats } from '../store'
import { fmtTime, fmtDur, speakerColor } from '../types'
import type { TurnEvent } from '../types'

/* ---------------- 布局参数 ---------------- */
const PX_PER_SEC = 160
const RULER_H = 26
const SEG_TOP = 34
const SEG_PAD_BOTTOM = 16
const MIN_SEG_H = 44
const MIN_CANVAS_H = SEG_TOP + MIN_SEG_H + SEG_PAD_BOTTOM

const canvasEl = ref<HTMLCanvasElement | null>(null)
const scrollEl = ref<HTMLDivElement | null>(null)
const follow = ref(true)

/** 画布高度：填满滚动容器（分段随高度伸缩） */
function canvasHeight(): number {
  return Math.max(MIN_CANVAS_H, scrollEl.value?.clientHeight ?? MIN_CANVAS_H)
}

function segArea(): { y: number; h: number } {
  const h = canvasHeight()
  return { y: SEG_TOP, h: Math.max(MIN_SEG_H, h - SEG_TOP - SEG_PAD_BOTTOM) }
}

const hoverIdx = ref(-1)
const tooltip = ref<{
  ev: TurnEvent
  x: number
  y: number
  leftSide: boolean
} | null>(null)

const tooltipStyle = computed(() =>
  tooltip.value ? { left: `${tooltip.value.x}px`, top: `${tooltip.value.y}px` } : {},
)

const contentWidth = computed(() => {
  const dur = Math.max(store.clip?.duration ?? 0, store.progressT, cursorPos())
  return Math.max(containerWidth.value, dur * PX_PER_SEC)
})

const containerWidth = ref(600)
let raf = 0
let dpr = 1

function cursorPos(): number {
  return store.pos
}

/* ---------------- 绘制 ---------------- */
function draw(): void {
  const canvas = canvasEl.value
  if (!canvas) return
  const w = contentWidth.value
  const h = canvasHeight()
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  // 底纹
  ctx.fillStyle = '#0e1420'
  ctx.fillRect(0, 0, w, h)

  // 时间刻度
  const minor = 1
  const major = 5
  ctx.font = '10.5px ui-monospace, Menlo, monospace'
  ctx.textBaseline = 'middle'
  for (let t = 0; t * PX_PER_SEC <= w; t += minor) {
    const x = t * PX_PER_SEC
    const isMajor = t % major === 0
    ctx.strokeStyle = isMajor ? 'rgba(255,255,255,0.10)' : 'rgba(255,255,255,0.045)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x + 0.5, isMajor ? RULER_H : RULER_H - 6)
    ctx.lineTo(x + 0.5, h)
    ctx.stroke()
    if (isMajor) {
      ctx.fillStyle = '#5b6478'
      ctx.fillText(fmtTime(t), x + 4, RULER_H / 2)
    }
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.12)'
  ctx.beginPath()
  ctx.moveTo(0.5, RULER_H)
  ctx.lineTo(w, RULER_H)
  ctx.stroke()

  // 说话人分段
  const seg = segArea()
  const events = store.events
  for (let i = 0; i < events.length; i++) {
    const ev = events[i]
    const x = ev.start * PX_PER_SEC
    const segW = Math.max(2, (ev.end - ev.start) * PX_PER_SEC)
    const color = speakerColor(ev.speaker)
    const hovered = i === hoverIdx.value
    ctx.fillStyle = hovered ? color + '66' : color + '2e'
    ctx.strokeStyle = color + (hovered ? 'ee' : '99')
    ctx.lineWidth = hovered ? 1.6 : 1
    const y = seg.y
    roundRect(ctx, x + 0.5, y, Math.max(segW - 1, 2), seg.h, 6)
    ctx.fill()
    ctx.stroke()
    // 段内标签
    if (segW > 64) {
      ctx.fillStyle = color
      ctx.font = '600 11px ui-monospace, Menlo, monospace'
      ctx.textBaseline = 'middle'
      const label = `S${ev.speaker}`
      ctx.fillText(label, x + 8, y + seg.h / 2 - 7)
      if (segW > 150 && ev.text) {
        ctx.fillStyle = 'rgba(255,255,255,0.55)'
        ctx.font = '10.5px sans-serif'
        const maxW = segW - 16
        const text = truncate(ev.text, maxW, ctx)
        ctx.fillText(text, x + 8, y + seg.h / 2 + 9)
      }
    }
  }

  // 游标
  const pos = cursorPos()
  if (store.clip && pos > 0) {
    const x = pos * PX_PER_SEC
    if (x <= w) {
      const active = store.phase === 'streaming'
      ctx.fillStyle = active ? 'rgba(34,211,238,0.95)' : 'rgba(34,211,238,0.55)'
      ctx.fillRect(x - 1, RULER_H, 2, h - RULER_H)
      ctx.beginPath()
      ctx.moveTo(x - 6, RULER_H)
      ctx.lineTo(x + 6, RULER_H)
      ctx.lineTo(x, RULER_H - 8)
      ctx.closePath()
      ctx.fill()
    }
  }
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

function truncate(text: string, maxW: number, ctx: CanvasRenderingContext2D): string {
  if (ctx.measureText(text).width <= maxW) return text
  let t = text
  while (t.length > 1 && ctx.measureText(t + '…').width > maxW) {
    t = t.slice(0, -1)
  }
  return t + '…'
}

/* ---------------- 悬停提示 ---------------- */
function onMove(e: MouseEvent): void {
  const canvas = canvasEl.value
  if (!canvas || store.events.length === 0) return
  const rect = canvas.getBoundingClientRect()
  const t = (e.clientX - rect.left + (scrollEl.value?.scrollLeft ?? 0)) / PX_PER_SEC
  let found = -1
  for (let i = store.events.length - 1; i >= 0; i--) {
    const ev = store.events[i]
    if (t >= ev.start && t < ev.end) {
      found = i
      break
    }
  }
  hoverIdx.value = found
  if (found >= 0) {
    const ev = store.events[found]
    const localX = e.clientX - rect.left
    const maxW = (scrollEl.value?.clientWidth ?? 600) - 16
    tooltip.value = {
      ev,
      x: Math.min(localX, maxW - 30),
      y: segArea().y + segArea().h / 2,
      leftSide: localX > maxW - 250,
    }
  } else {
    tooltip.value = null
  }
}

function onLeave(): void {
  hoverIdx.value = -1
  tooltip.value = null
}

/* ---------------- 自动跟随 ---------------- */
watch(cursorPos, (pos) => {
  if (!follow.value) return
  const el = scrollEl.value
  if (!el) return
  const x = pos * PX_PER_SEC
  if (x > el.scrollLeft + el.clientWidth * 0.85 || x < el.scrollLeft) {
    el.scrollLeft = Math.max(0, x - el.clientWidth * 0.15)
  }
})

/* ---------------- 尺寸 / 循环绘制 ---------------- */
const resizeObs = new ResizeObserver(() => {
  const el = scrollEl.value
  if (el) containerWidth.value = el.clientWidth
})

onMounted(() => {
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  const el = scrollEl.value
  if (el) {
    containerWidth.value = el.clientWidth
    resizeObs.observe(el)
  }
  const tick = (): void => {
    draw()
    raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  resizeObs.disconnect()
})
</script>

<template>
  <section class="panel timeline-panel">
    <header class="panel-head">
      <h2>说话人时间轴</h2>
      <div class="legend">
        <span v-for="sp in speakerStats" :key="sp.speaker" class="legend-chip">
          <i class="swatch" :style="{ background: speakerColor(sp.speaker) }"></i>
          S{{ sp.speaker }}
          <b>{{ fmtDur(sp.duration) }}</b>
        </span>
        <span v-if="speakerStats.length === 0" class="legend-empty">等待说话人分段…</span>
      </div>
      <button
        class="follow-btn"
        :class="{ on: follow }"
        :title="follow ? '自动跟随游标' : '手动滚动'"
        @click="follow = !follow"
      >
        {{ follow ? '跟随' : '滚动' }}
      </button>
    </header>

    <div ref="scrollEl" class="timeline-scroll" @mousemove="onMove" @mouseleave="onLeave">
      <canvas ref="canvasEl" class="timeline-canvas"></canvas>

      <div v-if="!store.clip" class="tl-empty">
        <div class="tl-empty-ico">▤</div>
        <p>尚未加载音频</p>
        <span>从上方选择示例、上传或录音后，分段将在这里实时呈现</span>
      </div>
      <div v-else-if="store.events.length === 0 && store.phase === 'streaming'" class="tl-empty faint">
        <span class="scanline"></span>
        <p>正在分离说话人…</p>
      </div>

      <div v-if="tooltip" class="tl-tooltip" :class="{ left: tooltip.leftSide }" :style="tooltipStyle">
        <div class="tip-time">{{ fmtTime(tooltip.ev.start) }} – {{ fmtTime(tooltip.ev.end) }}</div>
        <div class="tip-spk" :style="{ color: speakerColor(tooltip.ev.speaker) }">
          S{{ tooltip.ev.speaker }}
        </div>
        <div class="tip-text">{{ tooltip.ev.text || '（无文本）' }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.timeline-panel {
  min-height: 0;
}

.legend {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
  background: var(--card-2);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  padding: 2px 10px 2px 6px;
  font-family: var(--mono);
}

.legend-chip b {
  color: var(--text);
  font-weight: 600;
}

.swatch {
  width: 9px;
  height: 9px;
  border-radius: 3px;
}

.legend-empty {
  font-size: 12px;
  color: var(--text-faint);
}

.follow-btn {
  flex: none;
  padding: 4px 12px;
  font-size: 12px;
  font-family: var(--mono);
}

.follow-btn.on {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: rgba(34, 211, 238, 0.5);
}

.timeline-scroll {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  background:
    linear-gradient(rgba(255, 255, 255, 0.015), rgba(255, 255, 255, 0.015)),
    var(--bg-soft);
}

.timeline-canvas {
  display: block;
}

.tl-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--text-faint);
  pointer-events: none;
  text-align: center;
  padding: 16px;
}

.tl-empty p {
  font-size: 14px;
  color: var(--text-dim);
}

.tl-empty span {
  font-size: 12px;
}

.tl-empty-ico {
  font-size: 30px;
  opacity: 0.5;
}

.tl-empty.faint p {
  color: var(--text-faint);
}

.scanline {
  width: 220px;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  animation: scan 1.6s ease-in-out infinite;
}

@keyframes scan {
  0%, 100% {
    transform: translateX(-60px);
    opacity: 0.2;
  }
  50% {
    transform: translateX(60px);
    opacity: 1;
  }
}

.tl-tooltip {
  position: absolute;
  z-index: 5;
  transform: translate(14px, -50%);
  background: #0c111c;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  padding: 8px 12px;
  min-width: 190px;
  max-width: 300px;
  pointer-events: none;
}

.tl-tooltip.left {
  transform: translate(calc(-100% - 14px), -50%);
}

.tip-time {
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.tip-spk {
  font-family: var(--mono);
  font-weight: 700;
  font-size: 12px;
  margin-bottom: 3px;
}

.tip-text {
  font-size: 12.5px;
  color: var(--text);
  line-height: 1.4;
  word-break: break-word;
}
</style>
