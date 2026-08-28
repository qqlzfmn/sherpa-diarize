/** 说话人光谱色板：每个说话人被赋予一枚专属光谱色 */
import { theme } from '../composables/theme'
import { t } from '../composables/i18n'

/** 亮系高饱和光谱色（深色背景上直接使用） */
export const SPEAKER_COLORS = [
  '#ffb454', // 琥珀
  '#54c8ff', // 青蓝
  '#b98cff', // 紫罗兰
  '#5ef0b0', // 薄荷
  '#ff7ab2', // 玫瑰
  '#ffd166', // 金
  '#8be9fd', // 天蓝
  '#ff9e64', // 橘
] as const

/** 同色相的加深版（浅色背景上用作文本/描边，保证对比度） */
export const SPEAKER_COLORS_LIGHT = [
  '#b57a12', // 琥珀深
  '#0d7fb5', // 青蓝深
  '#7c4fe0', // 紫罗兰深
  '#0e9a68', // 薄荷深
  '#d63a85', // 玫瑰深
  '#b08500', // 金深
  '#1291bb', // 天蓝深
  '#c25e14', // 橘深
] as const

/** 当前主题下的说话人主色（响应式：主题切换即重渲染） */
export function speakerColor(id: number): string {
  const palette = theme.value === 'light' ? SPEAKER_COLORS_LIGHT : SPEAKER_COLORS
  return palette[id % palette.length]
}

/** 亮系原色：用于深色底上的色块标签（如时间轴 chip），两主题通用 */
export function speakerColorBright(id: number): string {
  return SPEAKER_COLORS[id % SPEAKER_COLORS.length]
}

export function speakerLabel(id: number): string {
  return t('common.speaker', { n: id + 1 })
}

/** '#rrggbb' + alpha → rgba() */
export function hexA(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function confPct(c: number): string {
  return `${Math.round(c * 100)}%`
}
