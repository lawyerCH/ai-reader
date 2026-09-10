import { describe, it, expect } from 'vitest'
import {
  formatWords, formatDuration, formatPercent, chapterLabel, sampleByDensity,
} from './format'

describe('formatters', () => {
  it('formats word counts in 万/亿', () => {
    expect(formatWords(25149)).toBe('3万')
    expect(formatWords(168000)).toBe('17万')
    expect(formatWords(340000000)).toBe('3.4亿')
    expect(formatWords(820)).toBe('820')
  })
  it('formats durations', () => {
    expect(formatDuration(4200)).toBe('1小时10分')
    expect(formatDuration(900)).toBe('15分钟')
  })
  it('clamps percent', () => {
    expect(formatPercent(0.55)).toBe('55%')
    expect(formatPercent(2)).toBe('100%')
  })
  it('labels chapters', () => {
    expect(chapterLabel(0, 9, '序')).toBe('1/9 · 序')
  })
  it('samples by density keeping top priority', () => {
    const items = Array.from({ length: 10 }, (_, i) => ({ priority: i / 10 }))
    expect(sampleByDensity(items, 'normal')).toHaveLength(4)
    expect(sampleByDensity(items, 'keyonly')[0].priority).toBe(0.9)
    expect(sampleByDensity(items, 'dense')).toHaveLength(10)
  })
})
