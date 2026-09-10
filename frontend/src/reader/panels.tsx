import { useEffect, useMemo, useState, useCallback } from 'react'
import {
  Sparkle, ChatCircleDots, Users, TreeStructure, MapPin, Books,
  ClockCounterClockwise, Detective, PencilSimple, GitFork, Download,
  PaperPlaneRight, Lightning, Brain, ShareNetwork, Heart,
} from '@phosphor-icons/react'
import { api } from '../api'
import type {
  Annotation, Character, Relation, TimelineEvent, Location, Setting, Foreshadow, Book,
} from '../types'
import { PersonaAvatar, DEFAULT_COLORS, PERSONA_LABEL } from '../components/PersonaAvatar'
import CharacterGraph from './CharacterGraph'

const PIDS = ['plot', 'lore', 'emotion', 'snark', 'professor', 'character']

/* ============ 批注面板 ============ */

export function AnnotationsPanel({
  book, chapterIdx, annotations, onOpenShare, onAsk,
}: {
  book: Book
  chapterIdx: number
  annotations: Annotation[]
  onOpenShare: (text: string, kind: string) => void
  onAsk: (q: string) => void
}) {
  const [digest, setDigest] = useState<any>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  useEffect(() => {
    setDigest(null)
    api.digest(book.id, chapterIdx).then(setDigest).catch(() => {})
  }, [book.id, chapterIdx])

  return (
    <div className="space-y-3">
      {digest?.summary && (
        <section className="rounded-xl border border-[var(--chrome-border)] bg-[var(--chrome-panel)] p-3">
          <h4 className="mb-1 flex items-center gap-1.5 text-xs font-bold text-[var(--brand-deep)]">
            <Books size={14} /> 章末小结 · {digest.title}
          </h4>
          <p className="text-[13px] leading-relaxed text-[var(--chrome-ink)]">{digest.summary}</p>
          {digest.golden?.length > 0 && (
            <div className="mt-2 space-y-1">
              {digest.golden.slice(0, 2).map((g: any, i: number) => (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-amber-50 px-2 py-1.5 text-xs text-amber-900">
                  <Sparkle size={13} className="mt-0.5 shrink-0" weight="fill" />
                  <span className="flex-1">{g.text}</span>
                  <button className="shrink-0 text-amber-700" title="生成金句海报"
                          onClick={() => onOpenShare(g.text, 'golden')}>
                    <ShareNetwork size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
      <h4 className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-[var(--chrome-muted)]">
        <span className="flex items-center gap-1"><Detective size={14} /> 本章 AI 批注（{annotations.length}）</span>
      </h4>
      {annotations.length === 0 && <p className="px-1 py-6 text-center text-xs text-[var(--chrome-muted)]">本章暂无批注，试试提高批注密度</p>}
      <div className="space-y-2">
        {annotations.map((a, i) => (
          <AnnotationCard key={a.id || i} a={a} chapterIdx={chapterIdx}
            onAsk={onAsk} onShare={onOpenShare} expanded={expanded === a.id}
            onToggle={() => setExpanded(expanded === a.id ? null : a.id)} />
        ))}
      </div>
    </div>
  )
}

function AnnotationCard({ a, chapterIdx, onAsk, onShare, expanded, onToggle }:
  { a: Annotation; chapterIdx: number; onAsk: (q: string) => void
    onShare: (text: string, kind: string) => void; expanded: boolean; onToggle: () => void }) {
  const likeKey = `ann-like-${a.id}`
  const [liked, setLiked] = useState<boolean>(() => localStorage.getItem(`ann-like-${a.id}`) === '1')
  const toggleLike = (e: React.MouseEvent) => {
    e.stopPropagation()
    const v = !liked
    setLiked(v)
    localStorage.setItem(likeKey, v ? '1' : '0')
  }
  return (
    <article className="rounded-xl border bg-white p-3 transition hover:shadow-sm"
             style={{ borderColor: `${DEFAULT_COLORS[a.persona]}44` }}>
      <button className="flex w-full items-start gap-2.5 text-left" onClick={onToggle}>
        <PersonaAvatar persona={a.persona} color={DEFAULT_COLORS[a.persona]} size={30} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold" style={{ color: DEFAULT_COLORS[a.persona] }}>
              {PERSONA_LABEL[a.persona]}
            </span>
            <span className="rounded bg-black/5 px-1.5 py-px text-[10px] text-[var(--chrome-muted)]">{a.title}</span>
          </div>
          <p className={`mt-1 text-[13px] leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>{a.content}</p>
          {a.quote && (
            <blockquote className="mt-1.5 border-l-2 pl-2 text-xs italic text-[var(--chrome-muted)]"
              style={{ borderColor: DEFAULT_COLORS[a.persona] }}>
              {a.quote}
            </blockquote>
          )}
        </div>
      </button>
      <div className="mt-2 flex items-center gap-1.5 pl-[42px]">
        <button className="chip text-[11px]" onDoubleClick={toggleLike}
                onClick={(e) => { if (!expanded) onToggle(); toggleLike(e) }}
                style={liked ? { background: '#fdecec', color: '#dc2626', borderColor: '#f3c2c2' } : undefined}>
          <Heart size={12} weight={liked ? 'fill' : 'regular'} /> 赞
        </button>
        {expanded && (
          <>
            <button className="chip text-[11px]" onClick={() => onAsk(`关于第${chapterIdx + 1}章这段内容“${a.quote || a.title}”，你怎么看？`)}>
              <ChatCircleDots size={12} /> 追问
            </button>
            <button className="chip text-[11px]" onClick={() => onShare(a.content, 'opinion')}>
              <ShareNetwork size={12} /> 分享观点
            </button>
          </>
        )}
      </div>
    </article>
  )
}

/* ============ 问答 / 读书会面板 ============ */

interface Msg {
  role: 'user' | 'persona'
  persona?: string
  content: string
  refs?: any[]
  mode?: string
}

const QUICK_QUESTIONS = [
  '主角是个什么样的人？',
  '目前埋了哪些伏笔？',
  '预测一下后续剧情',
  '这段在写法上有什么讲究？',
]

export function ChatPanel({
  book, chapterIdx, incoming, consumedIncoming,
}: {
  book: Book
  chapterIdx: number
  incoming: { text: string; mode?: string } | null
  consumedIncoming: () => void
}) {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'single' | 'discuss' | 'debate' | 'whatif'>('single')
  const [persona, setPersona] = useState('plot')
  const [chapterOnly, setChapterOnly] = useState(false)

  const send = useCallback(async (q: string, m = mode) => {
    if (!q.trim() || busy) return
    setMsgs((x) => [...x, { role: 'user', content: q, mode: m }])
    setBusy(true)
    try {
      const ci = chapterOnly ? chapterIdx : undefined
      if (m === 'discuss') {
        const r = await api.discuss(book.id, { q, chapter_idx: ci })
        setMsgs((x) => [...x, ...r.answers.map((a) => ({
          role: 'persona' as const, persona: a.persona, content: a.answer, refs: a.refs,
        }))])
      } else if (m === 'debate') {
        const r = await api.debate(book.id, { topic: q, chapter_idx: ci })
        setMsgs((x) => [...x, ...r.turns.map((t) => ({
          role: 'persona' as const, persona: t.persona, content: t.content,
        }))])
      } else if (m === 'whatif') {
        const r = await api.whatif(book.id, q)
        setMsgs((x) => [...x, ...r.answers.map((a) => ({
          role: 'persona' as const, persona: a.persona, content: a.content,
        }))])
      } else {
        const r = await api.ask(book.id, { q, persona, chapter_idx: ci })
        setMsgs((x) => [...x, { role: 'persona', persona, content: r.answer, refs: r.refs }])
      }
    } finally {
      setBusy(false)
    }
  }, [book.id, busy, mode, persona, chapterOnly, chapterIdx])

  useEffect(() => {
    if (incoming) {
      const m = incoming.mode === 'discuss' ? 'discuss' : incoming.mode === 'debate' ? 'debate' : 'single'
      setMode(m as any)
      send(incoming.text, m)
      consumedIncoming()
    }
  }, [incoming])

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex flex-wrap gap-1.5">
        {([['single', '单角色'], ['discuss', '读书会'], ['debate', '辩论'], ['whatif', '脑洞']] as const).map(
          ([k, l]) => (
            <button key={k} className={`chip text-[11px] ${mode === k ? 'on' : ''}`} onClick={() => setMode(k)}>
              {k === 'debate' ? <Lightning size={12} /> : k === 'whatif' ? <Brain size={12} /> : <ChatCircleDots size={12} />}
              {l}
            </button>
          ))}
      </div>
      {mode === 'single' && (
        <div className="mb-2 flex flex-wrap gap-1">
          {PIDS.map((p) => (
            <button key={p} onClick={() => setPersona(p)}
              className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${persona === p ? 'border-transparent text-white' : 'border-[var(--chrome-border)]'}`}
              style={persona === p ? { background: DEFAULT_COLORS[p] } : {}}>
              <PersonaAvatar persona={p} color={DEFAULT_COLORS[p]} size={16} />
              {PERSONA_LABEL[p]}
            </button>
          ))}
        </div>
      )}
      <label className="mb-2 flex items-center gap-1.5 text-[11px] text-[var(--chrome-muted)]">
        <input type="checkbox" checked={chapterOnly} onChange={(e) => setChapterOnly(e.target.checked)} />
        只讨论当前章节
      </label>

      <div className="scroll-area min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {msgs.length === 0 && (
          <div className="space-y-2 py-2">
            <p className="text-xs text-[var(--chrome-muted)]">向 AI 读书会提问，或试试：</p>
            {QUICK_QUESTIONS.map((q) => (
              <button key={q} className="block w-full rounded-lg border border-dashed border-[var(--chrome-border)] px-3 py-2 text-left text-xs hover:bg-amber-50"
                onClick={() => send(q)}>{q}</button>
            ))}
          </div>
        )}
        {msgs.map((m, i) => <MsgBubble key={i} m={m} />)}
        {busy && <div className="flex items-center gap-2 text-xs text-[var(--chrome-muted)]">
          <span className="typing-caret">AI 们正在翻书</span>
        </div>}
      </div>

      <div className="mt-2 flex gap-1.5">
        <input className="input flex-1 py-2 text-sm"
          placeholder={mode === 'whatif' ? '如果主角当时没有……' : mode === 'debate' ? '提出一个有争议的话题' : '关于这本书的任何问题…'}
          value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { send(input); setInput('') } }} />
        <button className="btn btn-primary px-3" disabled={busy} onClick={() => { send(input); setInput('') }}>
          <PaperPlaneRight size={16} />
        </button>
      </div>
    </div>
  )
}

function MsgBubble({ m }: { m: Msg }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[var(--brand)] px-3 py-2 text-sm text-white">
          {m.mode && m.mode !== 'single' && (
            <span className="mb-0.5 block text-[10px] opacity-80">
              {m.mode === 'discuss' ? '读书会话题' : m.mode === 'debate' ? '辩论话题' : '脑洞假设'}
            </span>
          )}
          {m.content}
        </div>
      </div>
    )
  }
  return (
    <div className="flex gap-2">
      <PersonaAvatar persona={m.persona || 'plot'} color={DEFAULT_COLORS[m.persona || 'plot']} size={26} />
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-[var(--chrome-border)] bg-white p-2.5">
        <span className="text-[11px] font-bold" style={{ color: DEFAULT_COLORS[m.persona || 'plot'] }}>
          {PERSONA_LABEL[m.persona || 'plot']}
        </span>
        <p className="mt-0.5 whitespace-pre-wrap text-[13px] leading-relaxed">{m.content}</p>
        {m.refs && m.refs.length > 0 && (
          <div className="mt-1.5 space-y-1 border-t border-dashed border-[var(--chrome-border)] pt-1.5">
            {m.refs.slice(0, 2).map((r, i) => (
              <p key={i} className="text-[11px] italic text-[var(--chrome-muted)]">
                《{r.title}》：{r.text}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ============ 图谱面板 ============ */

export function GraphPanel({ book }: { book: Book }) {
  const [chars, setChars] = useState<Character[]>([])
  const [rels, setRels] = useState<Relation[]>([])
  const [detail, setDetail] = useState<Character | null>(null)
  useEffect(() => {
    Promise.all([api.characters(book.id), api.relations(book.id)]).then(([c, r]) => {
      setChars(c); setRels(r)
    })
  }, [book.id])

  async function select(name: string) {
    try { setDetail(await api.character(book.id, name)) } catch { setDetail(null) }
  }

  return (
    <div className="flex h-full flex-col">
      <h4 className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[var(--chrome-muted)]">
        <Users size={14} /> 人物关系图谱（点击人物查看档案）
      </h4>
      <div className="scroll-area min-h-0 flex-1 overflow-y-auto rounded-xl border border-[var(--chrome-border)] bg-white">
        <CharacterGraph characters={chars} relations={rels} onSelect={select} />
      </div>
      {detail && (
        <div className="pop mt-2 max-h-56 overflow-y-auto rounded-xl border border-[var(--chrome-border)] bg-white p-3">
          <div className="mb-1 flex items-center justify-between">
            <b className="text-sm">{detail.name}</b>
            <button className="text-xs text-[var(--chrome-muted)]" onClick={() => setDetail(null)}>关闭</button>
          </div>
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--chrome-ink)]">{detail.profile}</p>
        </div>
      )}
    </div>
  )
}

/* ============ 探索面板：人物/时间线/地点/百科/伏笔 ============ */

export function ExplorePanel({ book, chapterIdx, onJump }: { book: Book; chapterIdx: number; onJump: (ch: number) => void }) {
  const [tab, setTab] = useState<'chars' | 'time' | 'map' | 'wiki' | 'fs'>('chars')
  const [data, setData] = useState<any>(null)
  useEffect(() => {
    const loaders = {
      chars: () => api.characters(book.id),
      time: () => api.timeline(book.id),
      map: () => api.locations(book.id),
      wiki: () => api.settings(book.id),
      fs: () => api.foreshadows(book.id),
    }
    loaders[tab]().then(setData)
  }, [tab, book.id])

  const tabs = [
    ['chars', '人物', <Users key="u" size={13} />],
    ['time', '时间线', <ClockCounterClockwise key="t" size={13} />],
    ['map', '地图', <MapPin key="m" size={13} />],
    ['wiki', '百科', <Books key="b" size={13} />],
    ['fs', '伏笔', <TreeStructure key="f" size={13} />],
  ] as const

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex gap-1 overflow-x-auto">
        {tabs.map(([k, l, ic]) => (
          <button key={k} className={`chip shrink-0 text-[11px] ${tab === k ? 'on' : ''}`} onClick={() => setTab(k as any)}>
            {ic}{l}
          </button>
        ))}
      </div>
      <div className="scroll-area min-h-0 flex-1 overflow-y-auto pr-1">
        {!data ? <p className="py-8 text-center text-xs text-[var(--chrome-muted)]">加载中…</p>
          : tab === 'chars' ? <CharList items={data as Character[]} onOpen={api.character.bind(null, book.id)} />
          : tab === 'time' ? <Timeline items={data as TimelineEvent[]} onJump={onJump} />
          : tab === 'map' ? <MapView items={data as Location[]} onJump={onJump} />
          : tab === 'wiki' ? <Wiki items={data as Setting[]} />
          : <Foreshadows items={data as Foreshadow[]} onJump={onJump} />}
      </div>
    </div>
  )
}

function CharList({ items, onOpen }: { items: Character[]; onOpen: (name: string) => Promise<Character> }) {
  const [d, setD] = useState<Character | null>(null)
  const roleLabel = { protagonist: '主角', supporting: '重要人物', minor: '次要人物' }
  return (
    <div className="space-y-2">
      {d && (
        <div className="pop sticky top-0 z-10 rounded-xl border border-[var(--chrome-border)] bg-[var(--chrome-panel)] p-3 shadow-card">
          <div className="flex justify-between"><b className="text-sm">{d.name}</b>
            <button className="text-xs text-[var(--chrome-muted)]" onClick={() => setD(null)}>关闭</button></div>
          <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed">{d.profile}</p>
        </div>
      )}
      {items.map((c) => (
        <button key={c.name} onClick={() => onOpen(c.name).then(setD)}
          className="flex w-full items-center gap-3 rounded-xl border border-[var(--chrome-border)] bg-white p-2.5 text-left hover:shadow-sm">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
            style={{ background: c.role === 'protagonist' ? '#DC4F3B' : c.role === 'supporting' ? '#b45309' : '#8a8070' }}>
            {c.name.slice(0, 2)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-2 text-sm font-semibold">
              {c.name}
              <span className="rounded bg-black/5 px-1.5 text-[10px] font-normal text-[var(--chrome-muted)]">
                {roleLabel[c.role]}
              </span>
            </span>
            <span className="block truncate text-[11px] text-[var(--chrome-muted)]">
              {c.traits.length ? `性格：${c.traits.join('、')} · ` : ''}提及 {c.mentions} 次 · 开口 {c.quote_count} 次
            </span>
          </span>
        </button>
      ))}
    </div>
  )
}

function Timeline({ items, onJump }: { items: TimelineEvent[]; onJump: (ch: number) => void }) {
  return (
    <div className="relative pl-4">
      <span className="absolute bottom-1 left-[5px] top-1 w-px bg-[var(--chrome-border)]" />
      {items.map((e, i) => (
        <button key={i} onClick={() => onJump(e.chapter)}
          className="relative mb-3 block w-full rounded-xl border border-[var(--chrome-border)] bg-white p-2.5 text-left">
          <span className="absolute -left-[15px] top-3 h-2.5 w-2.5 rounded-full bg-[var(--brand-soft)]" />
          <div className="text-[10px] font-bold text-[var(--brand-deep)]">第{e.chapter + 1}章 · {e.time}</div>
          <p className="mt-0.5 text-xs leading-relaxed">{e.summary}</p>
          {e.chars?.length > 0 && <p className="mt-1 text-[10px] text-[var(--chrome-muted)]">在场：{e.chars.slice(0, 4).join('、')}</p>}
        </button>
      ))}
    </div>
  )
}

function MapView({ items, onJump }: { items: Location[]; onJump: (ch: number) => void }) {
  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-xl border border-[var(--chrome-border)] bg-[#f3ecdd] p-3">
        <svg viewBox="0 0 300 220" className="w-full">
          {items.slice(0, 10).map((l, i) => {
            const a = (i / Math.max(1, Math.min(10, items.length))) * Math.PI * 2
            const x = 150 + Math.cos(a) * (i % 2 ? 70 : 105)
            const y = 110 + Math.sin(a) * (i % 2 ? 50 : 80)
            return (
              <g key={l.name} className="cursor-pointer" onClick={() => onJump(l.first_chapter)}>
                <line x1={150} y1={110} x2={x} y2={y} stroke="#c9b489" strokeDasharray="3 3" />
                <circle cx={x} cy={y} r={5 + Math.min(6, l.mentions)} fill="#b45309" opacity={0.75} />
                <text x={x} y={y - 9} fontSize={10} textAnchor="middle" fill="#5a4626">{l.name}</text>
              </g>
            )
          })}
          <circle cx={150} cy={110} r={7} fill="#7c3aed" />
          <text x={150} y={132} fontSize={9} textAnchor="middle" fill="#7c3aed">故事中心</text>
        </svg>
        <p className="text-center text-[10px] text-[var(--chrome-muted)]">点击地点跳转首次出场章</p>
      </div>
      {items.map((l) => (
        <button key={l.name} onClick={() => onJump(l.first_chapter)}
          className="block w-full rounded-xl border border-[var(--chrome-border)] bg-white p-2.5 text-left">
          <div className="flex items-center justify-between text-sm font-semibold">
            <span className="flex items-center gap-1"><MapPin size={13} className="text-[var(--brand)]" />{l.name}</span>
            <span className="text-[10px] font-normal text-[var(--chrome-muted)]">提及 {l.mentions} 次</span>
          </div>
          {l.desc && <p className="mt-0.5 line-clamp-2 text-[11px] text-[var(--chrome-muted)]">{l.desc}</p>}
        </button>
      ))}
    </div>
  )
}

function Wiki({ items }: { items: Setting[] }) {
  const groups = useMemo(() => {
    const g: Record<string, Setting[]> = {}
    items.forEach((s) => { (g[s.type] ||= []).push(s) })
    return g
  }, [items])
  return (
    <div className="space-y-3">
      {Object.entries(groups).map(([type, list]) => (
        <section key={type}>
          <h5 className="mb-1.5 text-[11px] font-bold text-[var(--brand-deep)]">{type}</h5>
          <div className="space-y-1.5">
            {list.map((s) => (
              <details key={s.term} className="rounded-lg border border-[var(--chrome-border)] bg-white p-2">
                <summary className="cursor-pointer text-sm font-medium">{s.term}</summary>
                <p className="mt-1 text-xs leading-relaxed text-[var(--chrome-ink)]">
                  {s.summary || `于第${s.first_chapter + 1}章首次出现，全书提及 ${s.mentions} 次。`}
                </p>
              </details>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function Foreshadows({ items, onJump }: { items: Foreshadow[]; onJump: (ch: number) => void }) {
  return (
    <div className="space-y-2">
      {items.map((f, i) => (
        <div key={i} className="rounded-xl border p-2.5"
          style={{ borderColor: f.status === 'resolved' ? '#0F766E44' : '#DC4F3B44', background: f.status === 'resolved' ? '#f0f9f8' : '#fdf2f0' }}>
          <div className="flex items-center gap-2 text-xs font-bold">
            {f.status === 'resolved'
              ? <><GitFork size={13} className="text-teal-700" /><span className="text-teal-700">已回收伏笔</span></>
              : <><Detective size={13} className="text-red-600" /><span className="text-red-600">悬而未决</span></>}
          </div>
          <button className="mt-1 block w-full text-left text-[12px] leading-relaxed" onClick={() => onJump(f.plant.chapter)}>
            <span className="text-[var(--chrome-muted)]">第{f.plant.chapter + 1}章埋：</span>{f.plant.text}
          </button>
          {f.payoff && (
            <button className="mt-1 block w-full text-left text-[12px] leading-relaxed" onClick={() => onJump(f.payoff!.chapter)}>
              <span className="text-teal-700">第{f.payoff.chapter + 1}章收：</span>{f.payoff.text}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

/* ============ 分支面板 ============ */

export function BranchesPanel({
  book, activeBranch, onActive, onRewrite, onExport, refreshKey,
}: {
  book: Book
  activeBranch: number | null
  onActive: (id: number | null) => void
  onRewrite: () => void
  onExport: (id: number) => void
  refreshKey: number
}) {
  const [branches, setBranches] = useState<any[]>([])
  const load = useCallback(() => api.branches(book.id).then(setBranches), [book.id])
  useEffect(() => { load() }, [load, refreshKey])
  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[var(--chrome-muted)]">
          <GitFork size={14} /> 读者分支（{branches.length}）
        </h4>
        <button className="btn btn-primary px-2.5 py-1.5 text-xs" onClick={onRewrite}>
          <PencilSimple size={13} /> 新改写
        </button>
      </div>
      <div className="scroll-area min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        <button onClick={() => onActive(null)}
          className={`w-full rounded-xl border p-2.5 text-left text-sm ${activeBranch === null ? 'border-[var(--brand)] bg-amber-50' : 'border-[var(--chrome-border)] bg-white'}`}>
          <b>原版</b>
          <p className="text-[11px] text-[var(--chrome-muted)]">作者的原始文本</p>
        </button>
        {branches.map((b) => (
          <div key={b.id}
            className={`rounded-xl border p-2.5 ${activeBranch === b.id ? 'border-[var(--brand)] bg-amber-50' : 'border-[var(--chrome-border)] bg-white'}`}>
            <button className="block w-full text-left" onClick={() => onActive(b.id === activeBranch ? null : b.id)}>
              <div className="flex items-center gap-1.5 text-sm font-semibold">
                <GitFork size={13} className="text-[var(--brand)]" />{b.name}
              </div>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-[var(--chrome-muted)]">{b.instruction}</p>
              <p className="mt-0.5 text-[10px] text-[var(--chrome-muted)]">
                第{b.chapter_idx + 1}章 · {b.scope === 'paragraph' ? '段落级' : b.scope === 'chapter' ? '章节级' : b.scope === 'ending' ? '结局改写' : '全篇'}
              </p>
            </button>
            <div className="mt-1.5 flex gap-1.5">
              <button className="chip text-[10px]" onClick={() => onExport(b.id)}><Download size={11} />导出</button>
              <button className="chip text-[10px]" onClick={async () => { await api.deleteBranch(book.id, b.id); load() }}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
