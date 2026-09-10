import { useMemo, useCallback, useEffect } from 'react'
import type { Annotation } from '../types'
import { DEFAULT_COLORS } from '../components/PersonaAvatar'
import type { SelectionTarget } from './SelectionBubble'

export interface ParaHighlight {
  start: number
  length: number
  color: string
  text: string
  para_idx?: number
}

interface Props {
  title: string
  paragraphs: string[]
  annotations: Annotation[]
  highlights: ParaHighlight[]
  overrides: Record<number, string>
  overrideBranch?: string
  chapterIdx: number
  onOpenAnnotation: (a: Annotation) => void
  onSelection: (t: SelectionTarget | null) => void
}

function renderWithHighlights(text: string, hs: ParaHighlight[]) {
  if (!hs.length) return text
  const sorted = [...hs].sort((a, b) => a.start - b.start)
  const parts: React.ReactNode[] = []
  let cursor = 0
  sorted.forEach((h, i) => {
    const s = Math.max(0, h.start), e = Math.min(text.length, s + h.length)
    if (s > cursor) parts.push(text.slice(cursor, s))
    parts.push(<mark key={i} className={`hl-${h.color}`}>{text.slice(s, e)}</mark>)
    cursor = Math.max(cursor, e)
  })
  if (cursor < text.length) parts.push(text.slice(cursor))
  return parts
}

export default function ReaderContent({
  title, paragraphs, annotations, highlights, overrides, overrideBranch,
  chapterIdx, onOpenAnnotation, onSelection,
}: Props) {
  const annByPara = useMemo(() => {
    const m: Record<number, Annotation[]> = {}
    annotations.forEach((a) => { (m[a.para_idx] ||= []).push(a) })
    return m
  }, [annotations])

  const hlMap = useMemo(() => {
    const m: Record<number, ParaHighlight[]> = {}
    ;(highlights as any[]).forEach((h) => {
      const pi = h.para_idx ?? 0
      ;(m[pi] ||= []).push(h)
    })
    return m
  }, [highlights])

  const handleSelection = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || !sel.rangeCount) return
    const range = sel.getRangeAt(0)
    const node = range.startContainer.parentElement?.closest('[data-para]')
    const endNode = range.endContainer.parentElement?.closest('[data-para]')
    if (!node || node !== endNode) return
    const paraEl = node as HTMLElement
    if (!paraEl.closest('.book-content')) return
    const paraIdx = Number(paraEl.getAttribute('data-para'))
    const text = range.toString().trim()
    if (text.length < 2) return
    // 计算在段落纯文本中的偏移
    const startOffset = getOffset(paraEl, range.startContainer, range.startOffset)
    const rect = range.getBoundingClientRect()
    onSelection({
      text, chapterIdx, paraIdx,
      startOffset,
      rect: { x: rect.left, y: rect.top, w: rect.width },
    } as SelectionTarget)
  }, [chapterIdx, onSelection])

  useEffect(() => {
    const up = () => {
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) onSelection(null)
    }
    document.addEventListener('selectionchange', up)
    return () => document.removeEventListener('selectionchange', up)
  }, [onSelection])

  return (
    <div className="book-content">
      <h2 className="chapter-title">{title}</h2>
      {overrideBranch && (
        <div className="mb-6 rounded-lg border border-dashed px-3 py-2 text-center text-xs"
             style={{ borderColor: 'var(--r-accent)', color: 'var(--r-accent)', textIndent: 0 }}>
          正在阅读读者分支：{overrideBranch}
        </div>
      )}
      {paragraphs.map((_, idx) => {
        const override = overrides[idx]
        const text = override ?? paragraphs[idx]
        const anns = annByPara[idx] || []
        return (
          <p key={idx} data-para={idx} className="para"
             style={override ? {
               background: 'color-mix(in srgb, var(--r-accent) 8%, transparent)',
               borderLeft: '3px solid var(--r-accent)', paddingLeft: '0.6em',
             } : undefined}>
            {renderWithHighlights(text, hlMap[idx] || [])}
            {anns.length > 0 && (
              <span className="ml-1 inline-flex items-center gap-[3px] align-middle"
                    style={{ textIndent: 0 }}>
                {anns.slice(0, 4).map((a, i) => (
                  <button key={a.id || i} className="anno-dot"
                    style={{ background: DEFAULT_COLORS[a.persona] || '#888' }}
                    onClick={(e) => { e.stopPropagation(); onOpenAnnotation(a) }}
                    title={a.title}>
                    {GLYPH[a.persona] || '·'}
                  </button>
                ))}
                {anns.length > 4 && (
                  <span className="text-[10px]" style={{ color: 'var(--r-muted)' }}>+{anns.length - 4}</span>
                )}
              </span>
            )}
          </p>
        )
      })}
    </div>
  )
}

const GLYPH: Record<string, string> = {
  plot: '剧', lore: '据', emotion: '情',
  snark: '槽', professor: '授', character: '角',
}

function getOffset(para: HTMLElement, node: Node, offset: number): number {
  let total = 0
  const walker = document.createTreeWalker(para, NodeFilter.SHOW_TEXT)
  let cur = walker.nextNode()
  while (cur) {
    if (cur === node) return total + offset
    total += (cur.textContent || '').length
    cur = walker.nextNode()
  }
  return total
}
