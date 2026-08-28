<script setup lang="ts">
import { computed } from 'vue'
import { session } from '../composables/session'
import { t, locale, setLocale } from '../composables/i18n'
import { theme, toggleTheme } from '../composables/theme'
import type { AsrMode } from '../types'
import StatusChip from './StatusChip.vue'

const props = defineProps<{ locked: boolean }>()

const modes = computed(() => {
  const m = session.models
  return [
    { value: 'none' as AsrMode, label: t('header.modeNone'), disabled: false, hint: t('header.modeNoneHint') },
    {
      value: 'offline' as AsrMode,
      label: t('header.modeOffline'),
      disabled: !m?.asr_offline_ready,
      hint: m?.asr_offline_ready ? t('header.modeOfflineHintReady') : t('header.modeOfflineHintNotReady'),
    },
    {
      value: 'streaming' as AsrMode,
      label: t('header.modeStreaming'),
      disabled: !m?.asr_streaming_ready,
      hint: m?.asr_streaming_ready ? t('header.modeStreamingHintReady') : t('header.modeStreamingHintNotReady'),
    },
  ]
})

const modelsBad = computed(() => session.models && !session.models.models_ready)
</script>

<template>
  <header class="head">
    <div class="brand">
      <div class="mark" aria-hidden="true">
        <i class="b b1" /><i class="b b2" /><i class="b b3" />
      </div>
      <div class="brand-txt">
        <h1>{{ t('brand.name') }}</h1>
        <p>{{ t('header.tagline') }}</p>
      </div>
    </div>

    <div class="right">
      <span class="edge-chip" :title="t('header.edgeTitle')">
        <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
          <circle cx="6" cy="6" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" />
          <circle cx="6" cy="6" r="1.6" fill="currentColor" />
        </svg>
        {{ t('header.edgeLabel') }}
      </span>

      <div class="mode" role="group" :aria-label="t('header.asrMode')">
        <span class="mode-label">{{ t('header.asrMode') }}</span>
        <button
          v-for="m in modes"
          :key="m.value"
          class="mode-btn"
          :class="{ on: session.asrMode === m.value }"
          :disabled="locked || m.disabled"
          :title="m.hint"
          @click="session.asrMode = m.value"
        >
          {{ m.label }}
        </button>
      </div>

      <div class="lang" role="group" :aria-label="t('header.langLabel')">
        <button
          class="lang-btn"
          :class="{ on: locale === 'zh' }"
          @click="setLocale('zh')"
        >
          中
        </button>
        <button
          class="lang-btn"
          :class="{ on: locale === 'en' }"
          @click="setLocale('en')"
        >
          EN
        </button>
      </div>

      <button class="theme-btn" :title="t('header.themeToggle')" data-theme-toggle @click="toggleTheme">
        <svg v-if="theme === 'dark'" viewBox="0 0 20 20" width="14" height="14" aria-hidden="true">
          <path d="M17.2 12.6A7.6 7.6 0 0 1 7.4 2.8a7.6 7.6 0 1 0 9.8 9.8z" fill="currentColor" />
        </svg>
        <svg v-else viewBox="0 0 20 20" width="14" height="14" aria-hidden="true">
          <circle cx="10" cy="10" r="3.4" fill="none" stroke="currentColor" stroke-width="1.7" />
          <g stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
            <path d="M10 1.8v2.1M10 16.1v2.1M1.8 10h2.1M16.1 10h2.1M4.2 4.2l1.5 1.5M14.3 14.3l1.5 1.5M15.8 4.2l-1.5 1.5M5.7 14.3l-1.5 1.5" />
          </g>
        </svg>
      </button>

      <StatusChip :phase="session.phase" />
    </div>

    <div v-if="modelsBad" class="warn-banner">
      ⚠ {{ t('header.modelsNotReady') }}
      <code>python3 scripts/download_models.py</code>
    </div>
  </header>
</template>

<style scoped>
.head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  height: 58px;
  padding: 0 18px;
  border-bottom: 1px solid var(--line-1);
  background: var(--header-bg);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.mark {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  width: 34px;
  height: 34px;
  padding: 7px 6px;
  border-radius: 10px;
  background: var(--bg-2);
  border: 1px solid var(--line-2);
  box-shadow: var(--shadow);
}
.b {
  width: 5px;
  border-radius: 2px;
}
.b1 {
  height: 11px;
  background: #ffb454;
}
.b2 {
  height: 20px;
  background: #54c8ff;
}
.b3 {
  height: 15px;
  background: #b98cff;
}
.brand-txt h1 {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.14em;
  line-height: 1.1;
}
.brand-txt p {
  font-size: 11px;
  color: var(--ink-low);
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.edge-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 10px;
  border-radius: 99px;
  background: rgba(94, 240, 176, 0.08);
  border: 1px solid rgba(94, 240, 176, 0.25);
  color: var(--good);
  font-size: 11.5px;
  white-space: nowrap;
}
.mode {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 30px;
  padding: 3px;
  border-radius: 99px;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
}
.mode-label {
  font-size: 11px;
  color: var(--ink-low);
  padding: 0 6px 0 8px;
  letter-spacing: 0.08em;
}
.mode-btn {
  height: 22px;
  padding: 0 12px;
  border-radius: 99px;
  font-size: 12px;
  color: var(--ink-mid);
  transition: all 0.18s var(--ease);
}
.mode-btn:hover:not(:disabled) {
  color: var(--ink-hi);
}
.mode-btn.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.mode-btn:disabled {
  opacity: 0.35;
}
.lang {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 28px;
  padding: 2px;
  border-radius: 99px;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
}
.lang-btn {
  height: 22px;
  padding: 0 8px;
  border-radius: 99px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--ink-mid);
  transition: all 0.15s var(--ease);
}
.lang-btn:hover {
  color: var(--ink-hi);
}
.lang-btn.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.theme-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--line-2);
  background: var(--bg-2);
  color: var(--ink-mid);
  transition: all 0.18s var(--ease);
}
.theme-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.warn-banner {
  position: absolute;
  left: 50%;
  top: 62px;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  background: rgba(255, 209, 102, 0.1);
  border: 1px solid rgba(255, 209, 102, 0.35);
  color: var(--warn);
  font-size: 12.5px;
  white-space: nowrap;
}
.warn-banner code {
  font-family: var(--font-mono);
  background: rgba(255, 209, 102, 0.12);
  padding: 1px 6px;
  border-radius: 5px;
}

@media (max-width: 1080px) {
  .brand-txt p {
    display: none;
  }
}
@media (max-width: 860px) {
  .edge-chip {
    display: none;
  }
}
</style>
