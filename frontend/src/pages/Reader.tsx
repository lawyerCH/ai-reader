import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  CaretLeft, List as ListIcon, GearSix, ShareNetwork, GitFork,
  ChatCircleDots, Detective, Users, Compass, TreeStructure,
  BookmarkSimple, ArrowLeft, ArrowRight, X, Sparkle, Scroll,
} from '@phosphor-icons/react'
import { api, wsUrl } from '../api'
import type {
  Book, Chapter, ChapterDetail, Annotation,
} from '../types'
import { useReaderStore, FONT_FAMILIES, READER_THEMES } from '../store'
import ReaderContent, { type ParaHighlight } from '../reader/ReaderContent'
import SettingsSheet from '../reader/SettingsSheet'
import SelectionBubble, { type SelectionTarget } from '../reader/SelectionBubble'
import RewriteSheet from '../reader/RewriteSheet'
import BranchTreeModal from '../reader/BranchTreeModal'
import ShareModal, { type ShareContext } from '../share/ShareModal'
import {
  AnnotationsPanel, ChatPanel, GraphPanel, ExplorePanel, BranchesPanel,
} from '../reader/panels'
import { DEFAULT_COLORS, PersonaAvatar, PERSONA_LABEL } from '../components/PersonaAvatar'

type PanelKind = 'annotations' | 'chat' | 'graph' | 'explore' | 'branches'

const PANEL_TABS: { id: PanelKind; label: string; icon: React.ReactNode }[] = [
  { id: 'annotations', label: '批注', icon: <Detective size={16} /> },
  { id: 'chat', label: '讨论', icon: <ChatCircleDots size={16} /> },
  { id: 'graph', label: '图谱', icon: <Users size={16} /> },
  { id: 'explore', label: '探索', icon: <Compass size={16} /> },
  { id: 'branches', label: '分支', icon: <GitFork size={16} /> },
]

export default function Reader() {
  const { id } = useParams()
  const bid = Number(id)
  const nav = useNavigate()
  const [sp, setSp] = useSearchParams()
  const settings = useReaderStore((s) => s.settings)

  const [book, setBook] = useState<Book | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterIdx, setChapterIdx] = useState(0)
  const [chapter, setChapter] = useState<ChapterDetail | null>(null)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [highlights, setHighlights] = useState<any[]>([])
  const [bookmarks, setBookmarks] = useState<any[]>([])

  const [panel, setPanel] = useState<PanelKind | null>(null)
  const [sheetPanel, setSheetPanel] = useState<PanelKind | null>(null)
  const [tocOpen, setTocOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [rewriteOpen, setRewriteOpen] = useState(false)
  const [treeOpen, setTreeOpen] = useState(false)
  const [share, setShare] = useState<ShareContext | null>(null)
  const [recap, setRecap] = useState<string | null>(null)

  const [selection, setSelection] = useState<SelectionTarget | null>(null)
  const [focusAnno, setFocusAnno] = useState<Annotation | null>(null)
  const [incoming, setIncoming] = useState<{ text: string; mode?: string } | null>(null)
  const [branchRefresh, setBranchRefresh] = useState(0)

  const [activeBranch, setActiveBranch] = useState<number | null>(
    sp.get('branch') ? Number(sp.get('branch')) : null)
  const [activeBranchName, setActiveBranchName] = useState('')
  const [overrideParas, setOverrideParas] = useState<string[] | null>(null)
  const [overrideMap, setOverrideMap] = useState<Record<number, string>>({})

  const [liveCount, setLiveCount] = useState(9999)
  const [percent, setPercent] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const pageRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(0)
  const [pageCount, setPageCount] = useState(1)
  const [trackW, setTrackW] = useState(0)
  const sessionStart = useRef(Date.now())
  const rewriteContext = useRef<{ paraIdx: number | null; text: string }>({ paraIdx: null, text: '' })
  const wsRef = useRef<WebSocket | null>(null)
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  // ---------- 初始载入 ----------
  useEffect(() => {
    Promise.all([api.book(bid), api.chapters(bid), api.progress.get(bid)])
      .then(async ([b, chs, pr]) => {
        setBook(b); setChapters(chs)
        const start = Math.min(pr.chapter_idx || 0, Math.max(0, chs.length - 1))
        setChapterIdx(start)
        // 重新打开时给前情提要
        if (pr.percent > 0.05) api.recap(bid, start).then((r) => setRecap(r.text)).catch(() => {})
      })
      .catch(() => nav('/'))
  }, [bid])

  // ---------- 实时陪读 WS ----------
  const connectReadAlong = useCallback((idx: number) => {
    if (!settings.autoAnnotations) { setLiveCount(9999); return }
    wsRef.current?.close()
    const ws = new WebSocket(wsUrl(`/ws/read/${bid}`))
    wsRef.current = ws
    let n = 0
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data)
      if (m.event === 'annotation') { n += 1; setLiveCount(n) }
      if (m.event === 'done') setLiveCount(9999)
    }
    ws.onerror = () => setLiveCount(9999)
    ws.onopen = () => ws.send(JSON.stringify({
      chapter: idx, density: settings.density,
      personas: settings.enabledPersonas,
    }))
  }, [bid, settings.autoAnnotations, settings.density, settings.enabledPersonas])


  const loadChapter = useCallback(async (idx: number, keepPanel?: boolean, chsOverride?: Chapter[]) => {
    const chs = chsOverride || chapters
    if (idx < 0 || idx >= chs.length) return
    setChapterIdx(idx)
    const [detail, anns, hls, bms] = await Promise.all([
      api.chapter(bid, idx),
      api.annotations(bid, { chapter: idx, density: settings.density, personas: settings.enabledPersonas }),
      api.highlights.list(bid),
      api.bookmarks.list(bid),
    ])
    setChapter(detail)
    setAnnotations(anns)
    setHighlights(hls.filter((h) => h.chapter_idx === idx))
    setBookmarks(bms.filter((b) => b.chapter_idx === idx))
    setPage(0)
    requestAnimationFrame(() => scrollRef.current?.scrollTo({ top: 0 }))
    api.progress.put(bid, {
      chapter_idx: idx, para_idx: 0, percent: (idx + 0.1) / Math.max(1, chs.length),
    })
    if (!keepPanel && window.innerWidth < 1024) setSheetPanel(null)
    setLiveCount(0)
    connectReadAlong(idx)
  }, [bid, chapters, settings.density, settings.enabledPersonas, connectReadAlong])

  useEffect(() => {
    if (chapters.length && chapterIdx < chapters.length) loadChapter(chapterIdx, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterIdx, chapters.length])

  // 密度/角色变更重新拉批注
  useEffect(() => {
    if (!chapter) return
    api.annotations(bid, { chapter: chapterIdx, density: settings.density, personas: settings.enabledPersonas })
      .then(setAnnotations)
  }, [settings.density, settings.enabledPersonas, bid, chapterIdx])

  // ---------- 阅读计时 ----------
  useEffect(() => {
    const t = setInterval(() => {
      const secs = Math.round((Date.now() - sessionStart.current) / 1000)
      if (secs >= 25 && chapter) {
        api.session(bid, 25, Math.round(chapter.word_count / Math.max(1, chapter.paragraphs.length) * 12)).catch(() => {})
        sessionStart.current = Date.now()
      }
    }, 25000)
    return () => clearInterval(t)
  }, [bid, chapter])

  // ---------- 分支覆盖 ----------
  const applyBranch = useCallback(async (brId: number | null, name = '') => {
    setActiveBranch(brId)
    setActiveBranchName(name)
    setSp(brId ? { branch: String(brId) } : {})
    setOverrideParas(null); setOverrideMap({})
    if (brId == null) return
    const m = await api.materialized(bid, brId)
    // 找影响当前章的最新覆盖
    for (const o of [...m.overrides].reverse()) {
      if (o.chapter_idx === chapterIdx) {
        if (o.scope === 'paragraph') {
          const map: Record<number, string> = {}
          const start = o.start_para ?? o.para_idx ?? 0
          o.paragraphs.forEach((p: string, i: number) => { map[start + i] = p })
          setOverrideMap(map)
        } else {
          setOverrideParas(o.paragraphs)
        }
        break
      }
    }
  }, [bid, chapterIdx, setSp])

  useEffect(() => { if (activeBranch != null) applyBranch(activeBranch, activeBranchName) /* eslint-disable-next-line */ }, [chapterIdx])

  const shownParagraphs = useMemo(() => {
    if (!chapter) return []
    return overrideParas && overrideParas.length ? overrideParas : chapter.paragraphs
  }, [chapter, overrideParas])

  // ---------- 翻页（CSS columns 仿真） ----------
  useEffect(() => {
    if (settings.pageMode !== 'paged' || !pageRef.current) return
    const el = pageRef.current
    const measure = () => {
      const w = el.clientWidth
      setTrackW(w)
      const pages = Math.max(1, Math.round(el.scrollWidth / Math.max(1, w)))
      setPageCount(pages)
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [shownParagraphs, settings.pageMode, settings.fontSize, settings.lineHeight])

  useEffect(() => {
    if (settings.pageMode === 'paged' && pageRef.current) {
      pageRef.current.scrollTo({ left: page * pageRef.current.clientWidth, behavior: 'smooth' })
    }
  }, [page, settings.pageMode])

  function onScroll() {
    const el = scrollRef.current
    if (!el || !chapters.length) return
    const tall = el.scrollHeight > el.clientHeight * 1.25
    const ratio = el.scrollTop / Math.max(1, el.scrollHeight - el.clientHeight)
    const p = Math.min(1, (chapterIdx + ratio) / chapters.length)
    setPercent(p)
    api.progress.put(bid, { chapter_idx: chapterIdx, percent: p, para_idx: 0 })
    if (tall && ratio > 0.985) {
      const next = chapterIdx + 1
      if (next < chapters.length) setChapterIdx(next)
    }
  }

  // ---------- 划词操作 ----------
  function paraOffset(t: SelectionTarget): { start: number } {
    return { start: t.startOffset ?? 0 }
  }

  async function addHighlight(color: string) {
    if (!selection) return
    const start = paraOffset(selection).start
    await api.highlights.add(bid, {
      chapter_idx: selection.chapterIdx, para_idx: selection.paraIdx,
      start, length: selection.text.length, text: selection.text, color,
    })
    setHighlights((h) => [...h, {
      chapter_idx: selection.chapterIdx, para_idx: selection.paraIdx,
      start, length: selection.text.length, text: selection.text, color,
    }])
    window.getSelection()?.removeAllRanges()
    setSelection(null)
  }

  async function addBookmark() {
    if (!selection) return
    await api.bookmarks.add(bid, {
      chapter_idx: selection.chapterIdx, para_idx: selection.paraIdx,
      preview: selection.text.slice(0, 40),
    })
    setSelection(null)
  }

  function askSelection() {
    const t = selection?.text || ''
    setPanel('chat'); setSheetPanel('chat')
    setIncoming({ text: `原文“${t.slice(0, 60)}”是什么意思？这里为什么这样写？`, mode: 'discuss' })
    setSelection(null); window.getSelection()?.removeAllRanges()
  }

  function rewriteSelection() {
    if (!selection) return
    rewriteContext.current = { paraIdx: selection.paraIdx, text: selection.text }
    setRewriteOpen(true); setSelection(null); window.getSelection()?.removeAllRanges()
  }

  function shareGolden() {
    if (!selection) return
    setShare({ kind: 'golden', text: selection.text })
    setSelection(null); window.getSelection()?.removeAllRanges()
  }

  function openAnnotation(a: Annotation) {
    setFocusAnno(a)
    if (isDesktop) setPanel('annotations')
    else setSheetPanel('annotations')
  }

  const fontFamily = FONT_FAMILIES.find((f) => f.id === settings.fontFamily)?.css
  const isDark = READER_THEMES.find((t) => t.id === settings.theme)?.dark
  const shownAnno = liveCount >= 9999 ? annotations : annotations.slice(0, liveCount)
  const totalWords = chapters.reduce((s, c) => s + c.word_count, 0) || book?.word_count || 1

  if (!book || !chapter) {
    return <div className="flex h-screen items-center justify-center text-[var(--chrome-muted)]">
      <Sparkle size={22} className="mr-2 animate-pulse" /> AI 读书会正在翻开这本书…
    </div>
  }

  return (
    <div className="reader-root fixed inset-0 flex flex-col reader-surface" data-theme={settings.theme}>
      {/* 顶栏 */}
      <header className="z-30 flex h-12 shrink-0 items-center gap-1 border-b px-2 sm:px-3"
        style={{ borderColor: 'var(--r-border)', background: 'var(--r-card)' }}>
        <button className="icon-btn" onClick={() => nav('/')} title="回书架" style={{ color: 'var(--r-fg)' }}>
          <CaretLeft size={20} />
        </button>
        <button className="icon-btn" onClick={() => setTocOpen((v) => !v)} title="目录"
                style={{ color: 'var(--r-fg)' }}>
          <ListIcon size={19} />
        </button>
        <div className="min-w-0 flex-1 px-1 leading-tight">
          <div className="truncate text-sm font-semibold" style={{ color: 'var(--r-fg)' }}>{book.title}</div>
          <div className="truncate text-[10px]" style={{ color: 'var(--r-muted)' }}>
            第{chapterIdx + 1}/{chapters.length}章 · {chapter.title}
            {activeBranchName && ` · 分支：${activeBranchName}`}
          </div>
        </div>
        <HeaderBtn icon={<GitFork size={18} />} label="分支树" onClick={() => setTreeOpen(true)} dark={!!isDark} />
        <HeaderBtn icon={<ShareNetwork size={18} />} label="分享" onClick={() => setShare({ kind: 'golden', text: chapter.paragraphs?.[0]?.slice(0, 40) })} dark={!!isDark} />
        <HeaderBtn icon={<GearSix size={18} />} label="设置" onClick={() => setSettingsOpen(true)} dark={!!isDark} />
        <div className="hidden items-center gap-1 lg:flex">
          {PANEL_TABS.map((t) => (
            <button key={t.id} title={t.label} onClick={() => setPanel(panel === t.id ? null : t.id)}
              className="icon-btn" style={{ color: panel === t.id ? 'var(--r-accent)' : 'var(--r-fg)' }}>
              {t.icon}
            </button>
          ))}
        </div>
      </header>
      <div className="read-progress-bar shrink-0">
        <div style={{ width: `${Math.round(percent * 100)}%`, background: 'var(--r-accent)' }} />
      </div>

      {/* 主体三栏 */}
      <div className="flex min-h-0 flex-1">
        {/* 左侧目录：移动端抽屉 / 桌面端固定栏 */}
        {tocOpen && (
          <>
            <div className="fixed inset-0 z-40 bg-black/35 lg:hidden" onClick={() => setTocOpen(false)} />
            <aside className="reader-surface fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col border-r shadow-sheet lg:static lg:z-auto lg:shadow-none"
                   style={{ borderColor: 'var(--r-border)' }}>
              <TocView chapters={chapters} current={chapterIdx} bookmarks={bookmarks}
                onJump={(i) => { setChapterIdx(i); setTocOpen(false) }}
                onClose={() => setTocOpen(false)} />
            </aside>
          </>
        )}

        {/* 中间正文 */}
        <main className="relative min-w-0 flex-1">
          {settings.pageMode === 'scroll' ? (
            <div ref={scrollRef} onScroll={onScroll}
              className="scroll-area h-full overflow-y-auto overscroll-contain">
              <div className="mx-auto max-w-[720px] px-5 py-7 sm:px-8 sm:py-10"
                   style={{ maxWidth: 'var(--r-measure, 720px)' }}>
                <ReaderContent
                  title={chapter.title}
                  paragraphs={shownParagraphs}
                  annotations={shownAnno}
                  highlights={highlights as ParaHighlight[]}
                  overrides={overrideMap}
                  overrideBranch={activeBranchName || undefined}
                  chapterIdx={chapterIdx}
                  onOpenAnnotation={openAnnotation}
                  onSelection={setSelection}
                />
                <ChapterEnd chapters={chapters} idx={chapterIdx}
                  onPrev={() => setChapterIdx(chapterIdx - 1)}
                  onNext={() => setChapterIdx(chapterIdx + 1)} />
              </div>
            </div>
          ) : (
            <div className="h-full px-3 py-4 sm:px-8">
              <div ref={pageRef}
                className="paged-track h-full rounded-lg"
                style={{ scrollSnapType: 'x mandatory' }}>
                <div style={{
                  height: '100%',
                  columnWidth: trackW ? `${trackW}px` : '360px',
                  columnGap: 0, columnFill: 'auto', padding: '12px 8px 36px',
                }}>
                  <div className="mx-auto" style={{ maxWidth: 'var(--r-measure, 680px)' }}>
                    <ReaderContent
                      title={chapter.title}
                      paragraphs={shownParagraphs}
                      annotations={shownAnno}
                      highlights={highlights as ParaHighlight[]}
                      overrides={overrideMap}
                      overrideBranch={activeBranchName || undefined}
                      chapterIdx={chapterIdx}
                      onOpenAnnotation={openAnnotation}
                      onSelection={setSelection}
                    />
                  </div>
                </div>
              </div>
              <div className="absolute inset-x-0 bottom-1 flex items-center justify-between px-5">
                <button className="icon-btn rounded-full bg-black/10" onClick={() => setChapterIdx(chapterIdx - 1)}
                  style={{ visibility: chapterIdx ? 'visible' : 'hidden', color: 'var(--r-fg)' }}>
                  <ArrowLeft size={18} />
                </button>
                <span className="text-xs" style={{ color: 'var(--r-muted)' }}>{page + 1}/{pageCount}</span>
                <button className="icon-btn rounded-full bg-black/10"
                  onClick={() => page + 1 < pageCount ? setPage(page + 1) : setChapterIdx(chapterIdx + 1)}
                  style={{ color: 'var(--r-fg)' }}>
                  <ArrowRight size={18} />
                </button>
              </div>
              {/* 点按翻页热区 */}
              <button className="absolute left-3 top-14 h-[calc(100%-5rem)] w-1/4"
                onClick={() => setPage(Math.max(0, page - 1))} aria-label="上一页" />
              <button className="absolute right-3 top-14 h-[calc(100%-5rem)] w-1/4"
                onClick={() => page + 1 < pageCount ? setPage(page + 1) : setChapterIdx(chapterIdx + 1)}
                aria-label="下一页" />
            </div>
          )}

          {/* 桌面端右栏 */}
          {panel && isDesktop && (
            <aside className="absolute inset-y-0 right-0 z-20 flex w-[400px] flex-col border-l bg-[var(--chrome-panel)]"
                   style={{ borderColor: 'var(--r-border)' }}>
              <PanelHeader tab={panel} onClose={() => setPanel(null)} onTab={setPanel} />
              <div className="scroll-area min-h-0 flex-1 overflow-y-auto p-3">
                {renderPanel(panel)}
              </div>
            </aside>
          )}
        </main>
      </div>

      {/* 移动端底部工具栏（桌面端由顶栏承担） */}
      <nav className="z-30 flex shrink-0 items-stretch justify-around border-t pt-1 safe-bottom lg:hidden"
        style={{ borderColor: 'var(--r-border)', background: 'var(--r-card)' }}>
        <MobileTab icon={<ListIcon size={20} />} label="目录" onClick={() => setTocOpen(true)} fg="var(--r-fg)" />
        <MobileTab icon={<Detective size={20} />} label="批注" onClick={() => setSheetPanel('annotations')} fg="var(--r-fg)" />
        <MobileTab center icon={<Sparkle size={24} weight="fill" />} label="改结局"
          onClick={() => { rewriteContext.current = { paraIdx: null, text: '' }; setRewriteOpen(true) }}
          fg="#fff" accent />
        <MobileTab icon={<ChatCircleDots size={20} />} label="讨论" onClick={() => setSheetPanel('chat')} fg="var(--r-fg)" />
        <MobileTab icon={<Compass size={20} />} label="更多" onClick={() => setSheetPanel(sheetPanel === 'explore' ? null : 'explore')} fg="var(--r-fg)" />
      </nav>

      {/* 移动端面板（底部弹层） */}
      {sheetPanel && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40 fade" onClick={() => setSheetPanel(null)} />
          <div className="reader-surface pop absolute inset-x-0 bottom-0 flex h-[72vh] flex-col rounded-t-2xl" data-theme={settings.theme}>
            <PanelHeader tab={sheetPanel} onClose={() => setSheetPanel(null)} onTab={(t) => setSheetPanel(t as PanelKind)} mobile />
            <div className="scroll-area min-h-0 flex-1 overflow-y-auto p-3">
              {renderPanel(sheetPanel)}
            </div>
          </div>
        </div>
      )}

      {/* 划词气泡 */}
      {selection && (
        <SelectionBubble
          target={selection}
          onClose={() => setSelection(null)}
          onHighlight={addHighlight}
          onAsk={askSelection}
          onRewrite={rewriteSelection}
          onPoster={shareGolden}
          onBookmark={addBookmark}
        />
      )}

      {/* 批注单卡（移动端点角标） */}
      {focusAnno && sheetPanel === 'annotations' && (
        <FocusAnnotation a={focusAnno} chapterIdx={chapterIdx}
          onClose={() => setFocusAnno(null)}
          onAsk={(q) => { setSheetPanel('chat'); setIncoming({ text: q, mode: 'single' }) }} />
      )}

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} bookId={bid} />
      <RewriteSheet
        book={book}
        open={rewriteOpen}
        chapterIdx={chapterIdx}
        paraIdx={rewriteContext.current.paraIdx}
        selectedText={rewriteContext.current.text}
        onClose={() => setRewriteOpen(false)}
        onReadBranch={(b, name) => { setRewriteOpen(false); setBranchRefresh((x) => x + 1); applyBranch(b, name); }}
      />
      <BranchTreeModal book={book} activeId={activeBranch} open={treeOpen}
        onPick={(id, name) => { applyBranch(id, name || ''); setTreeOpen(false) }}
        onClose={() => setTreeOpen(false)} />
      {share && (
        <ShareModal book={book}
          ctx={activeBranch != null && share.kind === 'golden'
            ? { kind: 'compare', branch: { name: activeBranchName, original: chapter.paragraphs.join('\n').slice(0, 500), rewritten: overrideParas?.join('\n') || '' } }
            : share}
          onClose={() => setShare(null)} />
      )}
      {recap && <RecapModal text={recap} totalWords={totalWords} onClose={() => setRecap(null)}
        onOpen={() => setSheetPanel('annotations')} />}
    </div>
  )

  function renderPanel(k: PanelKind) {
    if (k === 'annotations') return <AnnotationsPanel book={book!} chapterIdx={chapterIdx}
      annotations={annotations}
      onOpenShare={(text, kind) => setShare({ kind: kind as any, text, annotation: annotations.find((a) => a.content === text) })}
      onAsk={(q) => { setPanel('chat'); setSheetPanel('chat'); setIncoming({ text: q, mode: 'single' }) }} />
    if (k === 'chat') return <ChatPanel book={book!} chapterIdx={chapterIdx} incoming={incoming}
      consumedIncoming={() => setIncoming(null)} />
    if (k === 'graph') return <GraphPanel book={book!} />
    if (k === 'explore') return <ExploreView book={book!} chapterIdx={chapterIdx}
      onJump={(ch) => { setChapterIdx(ch); setSheetPanel(null); setTocOpen(false) }}
      onRewrite={() => { rewriteContext.current = { paraIdx: null, text: '' }; setRewriteOpen(true) }}
      onShare={() => setShare({ kind: 'notes' })}
      refresh={branchRefresh}
      activeBranch={activeBranch}
      onBranch={(id, name) => applyBranch(id, name)}
      setRefresh={() => setBranchRefresh((x) => x + 1)}
      exportUrl={(brId) => window.open(api.exportUrl(bid, `type=branch&branch_id=${brId}&format=markdown`), '_blank')} />
    if (k === 'branches') return <BranchesPanel book={book!} activeBranch={activeBranch}
      onActive={(id) => applyBranch(id, id == null ? '' : '我的改写')}
      onRewrite={() => { rewriteContext.current = { paraIdx: null, text: '' }; setRewriteOpen(true) }}
      onExport={(brId) => window.open(api.exportUrl(bid, `type=branch&branch_id=${brId}&format=markdown`), '_blank')}
      refreshKey={branchRefresh} />
    return null
  }
}

/* ---------------- 子视图 ---------------- */

function HeaderBtn({ icon, label, onClick, dark }:
  { icon: React.ReactNode; label: string; onClick: () => void; dark?: boolean }) {
  return (
    <button className="icon-btn" title={label} onClick={onClick}
      style={{ color: 'var(--r-fg)', width: 36, height: 36 }}>{icon}</button>
  )
}

function MobileTab({ icon, label, onClick, fg, center, accent }:
  { icon: React.ReactNode; label: string; onClick: () => void; fg: string; center?: boolean; accent?: boolean }) {
  if (center) {
    return (
      <button onClick={onClick} className="-mt-5 flex flex-col items-center" aria-label={label}>
        <span className="flex h-12 w-12 items-center justify-center rounded-full text-white shadow-lg"
          style={{ background: 'var(--r-accent)' }}>{icon}</span>
        <span className="text-[10px]" style={{ color: fg }}>{label}</span>
      </button>
    )
  }
  return (
    <button onClick={onClick} className="flex flex-1 flex-col items-center gap-0.5 py-1 text-[10px]"
      style={{ color: fg }}>
      {icon}{label}
    </button>
  )
}

function PanelHeader({ tab, onTab, onClose, mobile }:
  { tab: PanelKind; onTab: (t: PanelKind) => void; onClose: () => void; mobile?: boolean }) {
  return (
    <div className="flex items-center gap-1 border-b border-[var(--chrome-border)] px-2 py-1.5">
      {PANEL_TABS.map((t) => (
        <button key={t.id} onClick={() => onTab(t.id)}
          className={`flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium ${
            tab === t.id ? 'bg-[rgba(138,90,36,.12)] text-[var(--brand-deep)]' : 'text-[var(--chrome-muted)]'}`}>
          {t.icon}<span className="hidden sm:inline">{t.label}</span>
        </button>
      ))}
      <button className="icon-btn ml-auto" onClick={onClose}><X size={17} /></button>
      {mobile ? null : null}
    </div>
  )
}

function ExploreView(props: {
  book: Book; chapterIdx: number; onJump: (ch: number) => void
  onRewrite: () => void; onShare: () => void; refresh: number
  activeBranch: number | null; onBranch: (id: number, n: string) => void
  setRefresh: () => void; exportUrl: (id: number) => void
}) {
  const [sub, setSub] = useState<'explore' | 'branches'>('explore')
  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex gap-1">
        <button className={`chip text-[11px] ${sub === 'explore' ? 'on' : ''}`} onClick={() => setSub('explore')}>
          <Compass size={12} /> 全书探索
        </button>
        <button className={`chip text-[11px] ${sub === 'branches' ? 'on' : ''}`} onClick={() => setSub('branches')}>
          <GitFork size={12} /> 分支树
        </button>
        <button className="chip ml-auto text-[11px]" onClick={props.onShare}><ShareNetwork size={12} />笔记图</button>
      </div>
      <div className="min-h-0 flex-1">
        {sub === 'explore'
          ? <ExplorePanel book={props.book} chapterIdx={props.chapterIdx} onJump={props.onJump} />
          : <BranchesPanel book={props.book} activeBranch={props.activeBranch}
              onActive={(id) => props.onBranch(id ?? 0, '我的改写')} onRewrite={props.onRewrite}
              onExport={props.exportUrl} refreshKey={props.refresh} />}
      </div>
    </div>
  )
}

function TocView({ chapters, current, bookmarks, onJump, onClose }:
  { chapters: Chapter[]; current: number; bookmarks: any[]; onJump: (i: number) => void; onClose: () => void }) {
  return (
    <div className="reader-surface flex h-full flex-col" >
      <div className="flex h-11 items-center justify-between border-b px-3" style={{ borderColor: 'var(--r-border)' }}>
        <b className="text-sm" style={{ color: 'var(--r-fg)' }}>目录</b>
        <button className="icon-btn lg:hidden" onClick={onClose} style={{ color: 'var(--r-fg)' }}><X size={18} /></button>
      </div>
      <div className="scroll-area min-h-0 flex-1 overflow-y-auto p-2">
        {chapters.map((c, i) => (
          <button key={c.idx} onClick={() => onJump(i)}
            className={`mb-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
              i === current ? 'bg-[var(--r-accent)] font-semibold text-white' : ''}`}
            style={i === current ? {} : { color: 'var(--r-fg)' }}>
            <span className="min-w-0 flex-1 truncate">{c.title}</span>
            {bookmarks.some((b) => b.chapter_idx === i) && <BookmarkSimple size={13} weight="fill" />}
            <span className="text-[10px] opacity-70">{c.word_count}字</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function ChapterEnd({ chapters, idx, onPrev, onNext }:
  { chapters: Chapter[]; idx: number; onPrev: () => void; onNext: () => void }) {
  const last = idx === chapters.length - 1
  return (
    <div className="my-10 border-t border-dashed pt-6 text-center" style={{ borderColor: 'var(--r-border)' }}>
      <p className="mb-4 text-sm" style={{ color: 'var(--r-muted)' }}>
        {last ? '—— 全书完 ——' : `第 ${idx + 1} 章 完`}
      </p>
      <div className="flex justify-center gap-3">
        {idx > 0 && <button className="btn btn-ghost text-sm" onClick={onPrev}><ArrowLeft size={15} />上一章</button>}
        {!last && <button className="btn btn-primary text-sm" onClick={onNext}>下一章<ArrowRight size={15} /></button>}
      </div>
    </div>
  )
}

function FocusAnnotation({ a, chapterIdx, onClose, onAsk }:
  { a: Annotation; chapterIdx: number; onClose: () => void; onAsk: (q: string) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 lg:hidden" onClick={onClose}>
      <div className="pop w-full rounded-t-2xl bg-white p-4" onClick={(e) => e.stopPropagation()}>
        <div className="mb-2 flex items-center gap-2">
          <PersonaAvatar persona={a.persona} color={DEFAULT_COLORS[a.persona]} size={32} />
          <div>
            <div className="text-sm font-bold" style={{ color: DEFAULT_COLORS[a.persona] }}>{PERSONA_LABEL[a.persona]}</div>
            <div className="text-[11px] text-[var(--chrome-muted)]">{a.title} · 第{chapterIdx + 1}章</div>
          </div>
          <button className="icon-btn ml-auto" onClick={onClose}><X size={18} /></button>
        </div>
        <p className="text-[14px] leading-relaxed">{a.content}</p>
        {a.quote && <blockquote className="mt-2 border-l-2 pl-2 text-xs italic text-[var(--chrome-muted)]"
          style={{ borderColor: DEFAULT_COLORS[a.persona] }}>{a.quote}</blockquote>}
        <button className="btn btn-primary mt-3 w-full text-sm"
          onClick={() => onAsk(`关于第${chapterIdx + 1}章“${a.quote || a.title}”，展开说说？`)}>
          <ChatCircleDots size={15} /> 和 AI 继续讨论
        </button>
      </div>
    </div>
  )
}

function RecapModal({ text, totalWords, onClose, onOpen }:
  { text: string; totalWords: number; onClose: () => void; onOpen: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 fade">
      <div className="pop chrome-card w-full max-w-md p-5">
        <h2 className="mb-2 flex items-center gap-2 text-base font-bold">
          <Scroll size={19} className="text-[var(--brand)]" /> 欢迎回来，这是前情提要
        </h2>
        <pre className="scroll-area max-h-[50vh] whitespace-pre-wrap font-sans text-[13px] leading-relaxed">{text}</pre>
        <div className="mt-3 flex gap-2">
          <button className="btn btn-ghost flex-1" onClick={onClose}>直接开读</button>
          <button className="btn btn-primary flex-1" onClick={() => { onOpen(); onClose() }}>
            <TreeStructure size={15} /> 看本章批注
          </button>
        </div>
      </div>
    </div>
  )
}

function useMediaQuery(q: string) {
  const [v, setV] = useState(() => typeof window !== 'undefined' && window.matchMedia(q).matches)
  useEffect(() => {
    const m = window.matchMedia(q)
    const fn = () => setV(m.matches)
    m.addEventListener('change', fn)
    return () => m.removeEventListener('change', fn)
  }, [q])
  return v
}
