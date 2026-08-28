/** 时间格式化 */

/** 00:00 —— 走带时钟 */
export function fmtClock(sec: number): string {
  if (!isFinite(sec) || sec < 0) sec = 0
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/** 0:03.2 —— turn 时间戳（十分位） */
export function fmtStamp(sec: number): string {
  if (!isFinite(sec) || sec < 0) sec = 0
  const m = Math.floor(sec / 60)
  const s = sec - m * 60
  return `${m}:${s.toFixed(1).padStart(4, '0')}`
}

/** 处理耗时（毫秒 → 秒级时钟） */
export function fmtElapsed(ms: number): string {
  if (!ms) return '—'
  return fmtClock(ms / 1000)
}
