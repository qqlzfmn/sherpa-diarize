/** 说话人光谱色板：每个说话人被赋予一枚专属光谱色 */

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

export function speakerColor(id: number): string {
  return SPEAKER_COLORS[id % SPEAKER_COLORS.length]
}

export function speakerLabel(id: number): string {
  return `说话人 ${id + 1}`
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
