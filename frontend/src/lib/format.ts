export function formatWords(n: number): string {
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}亿`
  if (n >= 10_000) return `${Math.round(n / 10_000)}万`
  return n.toLocaleString()
}

export function formatDuration(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600)
    const m = Math.round((seconds % 3600) / 60)
    return m ? `${h}小时${m}分` : `${h}小时`
  }
  const m = Math.round(seconds / 60)
  return `${m}分钟`
}

export function formatPercent(p: number): string {
  return `${Math.round(Math.max(0, Math.min(1, p)) * 100)}%`
}

export function chapterLabel(idx: number, total: number, title: string): string {
  return `${idx + 1}/${total} · ${title}`
}

const DENSITY_KEEP: Record<string, number> = {
  dense: 99, normal: 4, sparse: 2, keyonly: 1,
}
export function sampleByDensity<T extends { priority: number }>(items: T[], density: string): T[] {
  const cap = DENSITY_KEEP[density] ?? 4
  return items.sort((a, b) => b.priority - a.priority).slice(0, cap)
}
