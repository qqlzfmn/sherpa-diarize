/**
 * 主题：dark / light。
 * 优先级：localStorage('sherpa-theme') > prefers-color-scheme: light > dark。
 * 状态写在 <html data-theme="dark|light">，CSS 令牌按属性切换。
 */
import { ref } from 'vue'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'sherpa-theme'

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'dark' || saved === 'light') return saved
  } catch {
    /* 隐私模式等场景忽略 */
  }
  if (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: light)').matches
  ) {
    return 'light'
  }
  return 'dark'
}

export const theme = ref<Theme>('dark')

/** 应用主题：更新响应式状态、<html data-theme> 与 localStorage */
export function applyTheme(t: Theme) {
  theme.value = t
  document.documentElement.dataset.theme = t
  try {
    localStorage.setItem(STORAGE_KEY, t)
  } catch {
    /* 忽略 */
  }
}

export function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

/* 模块加载即应用，避免首帧闪烁 */
applyTheme(initialTheme())
