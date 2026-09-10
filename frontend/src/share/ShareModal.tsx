import { useEffect, useMemo, useRef, useState } from 'react'
import { X, DownloadSimple, QrCode, Images } from '@phosphor-icons/react'
import { GIFEncoder, quantize, applyPalette } from 'gifenc'
import { api } from '../api'
import type { Book, Annotation } from '../types'
import { PERSONA_LABEL } from '../components/PersonaAvatar'
import {
  drawQuotePoster, drawOpinionPoster, drawNotesPoster,
  drawStatsPoster, drawCompareFrame, downloadCanvas, type PosterInput,
} from './poster'

export type ShareKind = 'golden' | 'opinion' | 'notes' | 'stats' | 'compare'

export interface ShareContext {
  kind: ShareKind
  text?: string
  annotation?: Annotation
  branch?: { name: string; original: string; rewritten: string }
}

async function loadQr(data: string): Promise<HTMLImageElement | null> {
  try {
    const url = api.qrUrl(data)
    const img = new Image()
    img.crossOrigin = 'anonymous'
    await new Promise<void>((res, rej) => {
      img.onload = () => res()
      img.onerror = () => rej(new Error('qr'))
      img.src = url
    })
    return img
  } catch { return null }
}

const TABS: { id: ShareKind; label: string }[] = [
  { id: 'golden', label: '金句海报' },
  { id: 'opinion', label: 'AI 观点图' },
  { id: 'notes', label: '笔记长图' },
  { id: 'stats', label: '数据海报' },
  { id: 'compare', label: '分支对比' },
]

export default function ShareModal({
  book, ctx, onClose,
}: { book: Book; ctx: ShareContext; onClose: () => void }) {
  const [tab, setTab] = useState<ShareKind>(ctx.kind === 'compare' ? 'compare' : ctx.kind)
  const [qr, setQr] = useState<HTMLImageElement | null>(null)
  const [gifBusy, setGifBusy] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [input, setInput] = useState<PosterInput | null>(null)

  const base = useMemo<PosterInput>(() => ({
    title: book.title, author: book.author,
    quote: ctx.kind === 'golden' ? ctx.text : undefined,
    opinion: ctx.kind === 'opinion'
      ? (ctx.annotation ? `【${PERSONA_LABEL[ctx.annotation.persona]}】${ctx.annotation.content}` : ctx.text)
      : undefined,
    persona: ctx.annotation?.persona,
    personaName: ctx.annotation ? PERSONA_LABEL[ctx.annotation.persona] : undefined,
    original: ctx.branch?.original,
    rewritten: ctx.branch?.rewritten,
    branchName: ctx.branch?.name,
  }), [book, ctx])

  useEffect(() => {
    loadQr(`${location.origin}/#/read/${book.id}`).then(setQr)
  }, [book.id])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const run = async () => {
      let data = { ...base, qr }
      if (tab === 'golden') {
        if (!data.quote) data.quote = '（从正文中选中一句金句，或在章末小结里点击分享）'
        drawQuotePoster(canvas, data)
      } else if (tab === 'opinion') {
        if (!data.opinion) data.opinion = '（在任意 AI 批注上点击“分享观点”）'
        drawOpinionPoster(canvas, data)
      } else if (tab === 'notes') {
        const anns = await api.annotations(book.id, { density: 'sparse' })
        const lines: string[] = []
        const chs = await api.chapters(book.id)
        let last = -1
        for (const a of anns.slice(0, 30)) {
          if (a.chapter_idx !== last) { lines.push(`〔${chs[a.chapter_idx]?.title || ''}〕`); last = a.chapter_idx }
          lines.push(`[${a.persona}]${a.content}`)
        }
        data.noteLines = lines
        drawNotesPoster(canvas, data)
      } else if (tab === 'stats') {
        const s = await api.statsOverview()
        const annTotal = Object.values(s.annotation_by_persona as Record<string, number>)
          .reduce((a, b) => a + b, 0)
        data.stats = [
          { label: '藏书（本）', value: String(s.book_count) },
          { label: '阅读字数', value: `${Math.round(s.words_read / 10000)}万` },
          { label: '阅读时长（小时）', value: String(Math.round(s.total_seconds / 3600)) },
          { label: '活跃天数', value: String(s.active_days) },
          { label: 'AI 批注（条）', value: String(annTotal) },
          { label: '读者分支（条）', value: String(s.branch_count) },
          { label: '读完（本）', value: String(s.finished_count) },
          { label: '在读（本）', value: String(s.reading_count) },
        ]
        drawStatsPoster(canvas, data)
      } else if (tab === 'compare') {
        drawCompareFrame(canvas, { ...data, qr }, false)
      }
      setInput(data)
    }
    run()
  }, [tab, qr, base, book.id])

  async function makeGif() {
    if (!input?.original) return
    setGifBusy(true)
    try {
      const size = { w: 750, h: 1000 }
      const c = document.createElement('canvas')
      const gif = GIFEncoder()
      for (const rewritten of [false, true, false]) {
        drawCompareFrame(c, { ...input, qr }, rewritten)
        const { data: px } = c.getContext('2d')!.getImageData(0, 0, size.w, size.h)
        const palette = quantize(px, 256)
        const index = applyPalette(px, palette)
        gif.writeFrame(index, size.w, size.h, { palette, delay: 1500 })
      }
      gif.finish()
      const blob = new Blob([gif.bytes() as unknown as BlobPart], { type: 'image/gif' })
      const a = document.createElement('a')
      a.download = `${book.title}-原版vs改写.gif`
      a.href = URL.createObjectURL(blob)
      a.click()
    } finally { setGifBusy(false) }
  }

  const visibleTabs = TABS.filter((t) => t.id !== 'compare' || !!ctx.branch)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 fade sm:items-center" onClick={onClose}>
      <div className="pop flex max-h-[94vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl bg-[var(--chrome-panel)] sm:rounded-2xl"
           onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center gap-2 border-b border-[var(--chrome-border)] px-5 py-3">
          <Images size={19} className="text-[var(--brand)]" />
          <h2 className="text-base font-bold">分享中心</h2>
          <div className="ml-2 hidden gap-1 overflow-x-auto sm:flex">
            {visibleTabs.map((t) => (
              <button key={t.id} className={`chip text-[11px] ${tab === t.id ? 'on' : ''}`} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </div>
          <button className="icon-btn ml-auto" onClick={onClose}><X size={19} /></button>
        </header>
        <div className="scroll-area grid flex-1 gap-4 overflow-y-auto p-4 sm:grid-cols-[1fr_230px]">
          <div className="flex justify-center overflow-y-auto rounded-xl bg-black/5 p-3">
            <canvas ref={canvasRef} className="max-h-[62vh] w-auto max-w-full rounded-lg shadow-card" />
          </div>
          <div className="space-y-3">
            <div className="flex gap-1 overflow-x-auto sm:flex-col">
              {visibleTabs.map((t) => (
                <button key={t.id} className={`chip whitespace-nowrap text-[11px] sm:w-full sm:justify-center ${tab === t.id ? 'on' : ''}`}
                  onClick={() => setTab(t.id)}>{t.label}</button>
              ))}
            </div>
            {tab === 'compare' && ctx.branch && (
              <button className="btn btn-primary w-full text-sm" disabled={gifBusy} onClick={makeGif}>
                <QrCode size={15} />{gifBusy ? '生成中…' : '生成原版⇄改写 GIF'}
              </button>
            )}
            <button className="btn btn-ghost w-full text-sm"
              onClick={() => canvasRef.current && downloadCanvas(canvasRef.current, `${book.title}-${tab}.png`)}>
              <DownloadSimple size={15} /> 下载图片
            </button>
            <div className="flex items-center gap-2 rounded-lg bg-black/5 p-2.5 text-[11px] text-[var(--chrome-muted)]">
              <QrCode size={26} className="shrink-0 text-[var(--brand)]" />
              海报自带二维码与书名，扫码可回到这本书的读书会；分支内容还可导出 TXT/Markdown/EPUB。
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
