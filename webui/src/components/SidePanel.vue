<script setup lang="ts">
import { computed } from 'vue'
import { session } from '../composables/session'
import { fmtClock, fmtElapsed, fmtStamp } from '../utils/time'
import { confPct, hexA, speakerColor, speakerLabel } from '../utils/speaker'
import { MODE_LABELS } from '../types'

interface SpkStat {
  id: number
  dur: number
  count: number
}

const stats = computed<SpkStat[]>(() => {
  const map = new Map<number, SpkStat>()
  for (const t of session.turns) {
    const s = map.get(t.speaker) ?? { id: t.speaker, dur: 0, count: 0 }
    s.dur += t.end - t.start
    s.count += 1
    map.set(t.speaker, s)
  }
  return [...map.values()].sort((a, b) => b.dur - a.dur)
})

const totalSpeech = computed(() => stats.value.reduce((acc, s) => acc + s.dur, 0))
const maxDur = computed(() => Math.max(...stats.value.map((s) => s.dur), 0))
const elapsed = computed(() => (session.endedAt ? session.endedAt - session.startedAt : 0))

const wsLabel = computed(() =>
  session.wsConnected ? '已连接' : session.phase === 'connecting' ? '连接中' : '未连接',
)
</script>

<template>
  <aside class="side">
    <!-- 说话人统计 -->
    <section class="panel stats">
      <h2 class="panel-title">说话人统计</h2>

      <div v-if="!stats.length" class="s-empty">
        {{ session.phase === 'processing' ? '分段生成中…' : '尚无说话人数据' }}
      </div>

      <ul v-else class="spk-list">
        <li v-for="s in stats" :key="s.id" class="spk">
          <div class="spk-head">
            <span class="spk-chip" :style="{ color: speakerColor(s.id) }">
              <i class="chip-dot" :style="{ background: speakerColor(s.id) }" />
              {{ speakerLabel(s.id) }}
            </span>
            <span class="spk-num mono">{{ s.count }} 段</span>
            <span class="spk-dur mono">{{ fmtClock(s.dur) }}</span>
            <span class="spk-pct mono">
              {{ totalSpeech ? Math.round((s.dur / totalSpeech) * 100) : 0 }}%
            </span>
          </div>
          <div class="bar">
            <i
              :style="{
                width: maxDur ? (s.dur / maxDur) * 100 + '%' : '0%',
                background: `linear-gradient(90deg, ${hexA(speakerColor(s.id), 0.55)}, ${speakerColor(s.id)})`,
              }"
            />
          </div>
        </li>
      </ul>

      <div v-if="stats.length" class="s-total">
        有效语音共 <b class="mono">{{ fmtClock(totalSpeech) }}</b>
        <span class="sep">·</span>
        识别到 <b>{{ session.speakersTotal || stats.length }}</b> 位说话人
      </div>
    </section>

    <!-- 处理详情 -->
    <section class="panel detail">
      <h2 class="panel-title">处理详情</h2>
      <dl class="kv">
        <div class="row"><dt>音频源</dt><dd>{{ session.sourceName || '—' }}</dd></div>
        <div class="row"><dt>识别模式</dt><dd>{{ session.asrMode ? MODE_LABELS[session.asrMode] : '—' }}</dd></div>
        <div class="row"><dt>连接状态</dt><dd class="mono">{{ wsLabel }}</dd></div>
        <div class="row"><dt>已处理</dt><dd class="mono">{{ fmtClock(session.progress) }}</dd></div>
        <div class="row"><dt>分段数</dt><dd class="mono">{{ session.turns.length }}</dd></div>
        <div class="row"><dt>说话人数</dt><dd class="mono">{{ session.speakersTotal || '—' }}</dd></div>
        <div class="row"><dt>处理耗时</dt><dd class="mono">{{ fmtElapsed(elapsed) }}</dd></div>
      </dl>
    </section>
  </aside>
</template>

<style scoped>
.side {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 280px;
  flex-shrink: 0;
  min-width: 0;
}
.panel {
  background: var(--bg-1);
  border: 1px solid var(--line-1);
  border-radius: var(--radius);
  padding: 12px 14px;
}
.panel-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--ink-mid);
  margin-bottom: 10px;
}
.s-empty {
  padding: 18px 0 14px;
  text-align: center;
  font-size: 12px;
  color: var(--ink-low);
}
.spk-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.spk-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}
.spk-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 12px;
}
.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.spk-num {
  color: var(--ink-low);
  margin-left: auto;
}
.spk-dur {
  color: var(--ink-hi);
  font-weight: 600;
}
.spk-pct {
  color: var(--ink-low);
  min-width: 38px;
  text-align: right;
}
.bar {
  margin-top: 5px;
  height: 5px;
  border-radius: 99px;
  background: var(--bg-3);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  transition: width 0.4s var(--ease);
}
.s-total {
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px dashed var(--line-1);
  font-size: 11.5px;
  color: var(--ink-low);
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}
.s-total b {
  color: var(--ink-mid);
  font-weight: 600;
}
.sep {
  opacity: 0.5;
}
.kv {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12px;
}
.row dt {
  color: var(--ink-low);
  min-width: 56px;
  flex-shrink: 0;
}
.row dd {
  color: var(--ink-mid);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
