<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { store, speakerStats } from '../store'
import { fmtTime, speakerColor } from '../types'

const listEl = ref<HTMLDivElement | null>(null)
const freshId = ref(-1)
let prevPartial: string | null = null
let freshTimer = 0

const totalTurns = computed(() => store.events.length)
const uniqueSpeakers = computed(() => new Set(store.events.map((e) => e.speaker)).size)

watch(
  () => [store.events.length, store.partialText] as const,
  ([len, partial]) => {
    // partial → final 的"平滑转白"：该事件行短暂带 fresh 类（灰 → 白渐变）
    if (prevPartial !== null && len > 0) {
      freshId.value = len - 1
      window.clearTimeout(freshTimer)
      freshTimer = window.setTimeout(() => {
        freshId.value = -1
      }, 900)
    }
    prevPartial = partial
    void nextTick(() => {
      const el = listEl.value
      if (el) el.scrollTop = el.scrollHeight
    })
  },
)

function chipStyle(speaker: number): Record<string, string> {
  const c = speakerColor(speaker)
  return {
    background: c + '22',
    color: c,
    border: `1px solid ${c}55`,
  }
}

const confText = (c: number): string => `${Math.round(c * 100)}%`
</script>

<template>
  <section class="panel transcript-panel">
    <header class="panel-head">
      <h2>实时转写</h2>
      <div class="tstats">
        <span class="stat-chip">共 <b>{{ totalTurns }}</b> 段</span>
        <span class="stat-chip">说话人 <b>{{ uniqueSpeakers }}</b> 位</span>
      </div>
    </header>

    <div ref="listEl" class="tlist">
      <div v-if="store.events.length === 0 && !store.partialText" class="tempty">
        <div class="tempty-ico">✎</div>
        <p>暂无转写结果</p>
        <span>开始处理后，每个说话人 turn 将逐行显示在这里</span>
      </div>

      <div
        v-for="ev in store.events"
        :key="ev.id"
        class="trow"
        :class="{ fresh: ev.id === freshId }"
      >
        <span class="time">{{ fmtTime(ev.start) }}–{{ fmtTime(ev.end) }}</span>
        <span class="spk" :style="chipStyle(ev.speaker)">S{{ ev.speaker }}</span>
        <span class="text">{{ ev.text || '（无文本）' }}</span>
        <span class="conf">{{ confText(ev.confidence) }}</span>
      </div>

      <div v-if="store.partialText" class="trow partial">
        <span class="time">…</span>
        <span class="spk">S?</span>
        <span class="text">
          {{ store.partialText }}
          <span class="caret"></span>
        </span>
      </div>
    </div>

    <footer v-if="speakerStats.length > 0" class="tfoot">
      <span
        v-for="sp in speakerStats"
        :key="sp.speaker"
        class="foot-chip"
        :style="{ color: speakerColor(sp.speaker) }"
      >
        <i class="swatch" :style="{ background: speakerColor(sp.speaker) }"></i>
        S{{ sp.speaker }} · {{ sp.turns }} 段
      </span>
    </footer>
  </section>
</template>

<style scoped>
.transcript-panel {
  min-height: 0;
}

.tstats {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.stat-chip {
  font-size: 12px;
  color: var(--text-dim);
  background: var(--card-2);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  padding: 2px 10px;
  font-family: var(--mono);
}

.stat-chip b {
  color: var(--text);
}

.tlist {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background:
    linear-gradient(rgba(255, 255, 255, 0.012), rgba(255, 255, 255, 0.012)),
    var(--bg-soft);
}

.tempty {
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--text-faint);
  text-align: center;
  padding: 24px;
}

.tempty p {
  font-size: 14px;
  color: var(--text-dim);
}

.tempty span {
  font-size: 12px;
}

.tempty-ico {
  font-size: 26px;
  opacity: 0.5;
}

.trow {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--card);
  border: 1px solid var(--border-soft);
  transition: border-color 0.2s ease;
}

.trow:hover {
  border-color: var(--border);
}

.time {
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.spk {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
}

.text {
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.5;
  word-break: break-word;
  min-width: 0;
}

.conf {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-faint);
  white-space: nowrap;
}

/* partial：灰色 + 呼吸感，明显区别于 final */
.trow.partial {
  background: rgba(255, 255, 255, 0.02);
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.09);
}

.trow.partial .spk {
  background: rgba(138, 148, 168, 0.15);
  color: var(--text-faint);
  border: 1px solid rgba(138, 148, 168, 0.3);
}

.trow.partial .text {
  color: var(--text-dim);
  font-style: italic;
  animation: breathe 1.7s ease-in-out infinite;
}

.caret {
  display: inline-block;
  width: 2px;
  height: 14px;
  margin-left: 4px;
  vertical-align: -2px;
  background: var(--text-dim);
  animation: blink 0.9s steps(2) infinite;
}

@keyframes breathe {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}

@keyframes blink {
  50% { opacity: 0; }
}

/* partial → final：灰 → 白平滑过渡 */
.trow.fresh .text {
  animation: partialToFinal 0.9s ease-out;
}

@keyframes partialToFinal {
  0% {
    color: var(--text-dim);
    opacity: 0.6;
    font-style: italic;
  }
  100% {
    color: var(--text);
    opacity: 1;
    font-style: normal;
  }
}

.tfoot {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid var(--border-soft);
  background: var(--card);
}

.foot-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-family: var(--mono);
}

.swatch {
  width: 8px;
  height: 8px;
  border-radius: 3px;
}
</style>
