<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { session } from '../composables/session'
import { fmtStamp } from '../utils/time'
import { confPct, hexA, speakerColor, speakerLabel } from '../utils/speaker'

const listEl = ref<HTMLElement | null>(null)

function scrollBottom() {
  const el = listEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  () => [session.turns.length, session.partial],
  () => nextTick(scrollBottom),
)

const modeName = () => {
  switch (session.asrMode) {
    case 'streaming':
      return '流式识别'
    case 'offline':
      return '离线转写'
    default:
      return '仅分离'
  }
}
</script>

<template>
  <section class="transcript panel">
    <div class="tr-head">
      <h2 class="panel-title">转写</h2>
      <span class="mode-tag">{{ modeName() }}</span>
      <span class="count mono">{{ session.turns.length }} 段</span>
      <span v-if="session.phase === 'processing'" class="live">
        <i class="pulse-dot" />实时
      </span>
    </div>

    <div ref="listEl" class="tr-list">
      <!-- 空状态 -->
      <div v-if="!session.turns.length && session.phase !== 'processing'" class="empty">
        <div class="empty-glyph" aria-hidden="true">
          <i /><i /><i />
        </div>
        <p class="empty-title">
          {{ session.phase === 'done' ? '未识别到语音分段' : '转写将在这里逐句呈现' }}
        </p>
        <p class="empty-sub">
          {{
            session.phase === 'done'
              ? '音频中可能没有清晰的人声，或 VAD 未命中。'
              : '流式模式下会先出现灰度预览，定型后转为正式文本。'
          }}
        </p>
      </div>

      <!-- turn 行 -->
      <article
        v-for="t in session.turns"
        :key="t.id"
        class="turn-row"
        :style="{ '--spk': speakerColor(t.speaker) }"
      >
        <div class="rail" />
        <div class="body">
          <div class="meta">
            <span class="time mono">{{ fmtStamp(t.start) }} – {{ fmtStamp(t.end) }}</span>
            <span class="spk" :style="{ color: speakerColor(t.speaker) }">
              {{ speakerLabel(t.speaker) }}
            </span>
            <span class="conf mono">置信 {{ confPct(t.confidence) }}</span>
          </div>
          <p class="text">{{ t.text || '（无语音内容）' }}</p>
        </div>
      </article>

      <!-- 流式 partial：未定型预览 -->
      <div v-if="session.phase === 'processing' && session.partial" class="turn-row partial">
        <div class="rail" />
        <div class="body">
          <div class="meta">
            <span class="ghost-tag"><i class="pulse-dot" />识别中</span>
            <span class="ghost-hint">文本尚未定型，最终结果到达后自动转为正式条目</span>
          </div>
          <p class="text ghost-text">{{ session.partial }}<span class="caret" /></p>
        </div>
      </div>

      <div v-if="session.phase === 'done' && session.turns.length" class="done-line">
        <i class="ok-dot" />全部完成 — 共识别 {{ session.speakersTotal }} 位说话人
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: var(--bg-1);
  border: 1px solid var(--line-1);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.transcript {
  flex: 1;
  min-width: 0;
}
.tr-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px 10px;
  border-bottom: 1px solid var(--line-1);
  flex-shrink: 0;
}
.panel-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--ink-mid);
}
.mode-tag {
  font-size: 11px;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 2px 8px;
  border-radius: 99px;
}
.count {
  font-size: 11px;
  color: var(--ink-low);
}
.live {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--good);
}
.pulse-dot {
  width: 6px;
  height: 6px;
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
    opacity: 0.35;
  }
}

.tr-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.empty {
  margin: auto;
  text-align: center;
  max-width: 320px;
  padding: 30px 10px;
}
.empty-glyph {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 5px;
  height: 30px;
  margin-bottom: 14px;
}
.empty-glyph i {
  width: 4px;
  border-radius: 2px;
  background: var(--ink-low);
  opacity: 0.55;
}
.empty-glyph i:nth-child(1) {
  height: 12px;
}
.empty-glyph i:nth-child(2) {
  height: 24px;
}
.empty-glyph i:nth-child(3) {
  height: 17px;
}
.empty-title {
  font-size: 13.5px;
  color: var(--ink-mid);
  font-weight: 600;
}
.empty-sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-low);
  line-height: 1.7;
}

.turn-row {
  display: flex;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line-1);
  background: var(--bg-2);
  overflow: hidden;
  animation: rise 0.32s var(--ease);
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(7px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.rail {
  width: 3px;
  flex-shrink: 0;
  background: var(--spk);
}
.body {
  flex: 1;
  min-width: 0;
  padding: 9px 12px 10px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.time {
  font-size: 11px;
  color: var(--ink-low);
}
.spk {
  font-size: 11.5px;
  font-weight: 700;
}
.conf {
  font-size: 11px;
  color: var(--ink-low);
}
.text {
  margin-top: 5px;
  font-size: 14.5px;
  line-height: 1.75;
  color: var(--ink-hi);
  letter-spacing: 0.015em;
  word-break: break-word;
}

/* ---- partial 幽灵预览：明显区别于最终文本 ---- */
.turn-row.partial {
  border-style: dashed;
  border-color: var(--line-2);
  background: transparent;
  animation: none;
}
.partial .rail {
  background: repeating-linear-gradient(
    180deg,
    var(--ink-low) 0 4px,
    transparent 4px 8px
  );
  opacity: 0.7;
}
.ghost-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--ink-low);
}
.ghost-hint {
  font-size: 11px;
  color: var(--ink-low);
  opacity: 0.75;
}
.ghost-text {
  color: var(--ink-low);
  font-style: italic;
  opacity: 0.85;
}
.caret {
  display: inline-block;
  width: 2px;
  height: 15px;
  margin-left: 4px;
  vertical-align: -2px;
  background: var(--ink-mid);
  animation: blink 0.9s steps(1) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

.done-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 6px 2px;
  font-size: 12px;
  color: var(--good);
}
.ok-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--good);
}
</style>
