import { useEffect, useMemo, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, PencilSimple, Trash, ArrowRight, SpinnerGap, MagnifyingGlass,
  Sparkle, CheckCircle, DotsThreeVertical,
} from '@phosphor-icons/react'
import { api } from '../api'
import type { Book } from '../types'
import ImportModal from '../components/ImportModal'
import BookEditModal from '../components/BookEditModal'
import { useUiStore } from '../store'

const STATUS_LABEL: Record<string, string> = {
  all: '全部', want: '想读', reading: '在读', finished: '已读', dropped: '搁置',
}
const STATUS_STYLE: Record<string, string> = {
  want: 'bg-slate-100 text-slate-600',
  reading: 'bg-amber-100 text-amber-800',
  finished: 'bg-emerald-100 text-emerald-700',
  dropped: 'bg-zinc-200 text-zinc-500',
}

export default function Bookshelf() {
  const nav = useNavigate()
  const [books, setBooks] = useState<Book[]>([])
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('updated')
  const [q, setQ] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [editing, setEditing] = useState<Book | null>(null)
  const [menuFor, setMenuFor] = useState<number | null>(null)
  const showToast = useUiStore((s) => s.showToast)

  const load = useCallback(async () => {
    setBooks(await api.books(`?sort=${sort}`))
  }, [sort])

  useEffect(() => { load() }, [load])

  // 分析中书籍轮询
  useEffect(() => {
    const pending = books.some((b) => b.analyze?.status === 'analyzing')
    if (!pending) return
    const t = setInterval(load, 2200)
    return () => clearInterval(t)
  }, [books, load])

  const filtered = useMemo(() => books.filter((b) =>
    (filter === 'all' || b.status === filter) &&
    (!q || b.title.includes(q) || (b.author || '').includes(q))),
    [books, filter, q])

  const totalWords = books.reduce((s, b) => s + b.word_count, 0)
  const annCount = (b: Book) => b.analyze?.result?.annotations || 0

  async function del(b: Book) {
    if (!confirm(`确定删除《${b.title}》？章节、批注与分支都会删除。`)) return
    await api.deleteBook(b.id)
    showToast('已删除')
    setMenuFor(null); load()
  }

  return (
    <div className="rise">
      {/* 顶部统计与导入 */}
      <section className="mb-6 mt-1 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-wide sm:text-3xl">我的书架</h1>
          <p className="mt-1 text-sm text-[var(--chrome-muted)]">
            {books.length} 本藏书 · {books.filter((b) => b.status === 'reading').length} 本在读 ·
            {' '}共 {(totalWords / 10000).toFixed(1)} 万字 · 每本书都有专属 AI 读书会
          </p>
        </div>
        <button className="btn btn-primary px-5 py-2.5 text-[15px] shadow-card" onClick={() => setShowImport(true)}>
          <Plus size={18} weight="bold" /> 导入小说
        </button>
      </section>

      {/* 筛选行 */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        {Object.entries(STATUS_LABEL).map(([k, l]) => (
          <button key={k} className={`chip ${filter === k ? 'on' : ''}`} onClick={() => setFilter(k)}>
            {l}
          </button>
        ))}
        <div className="relative ml-auto">
          <MagnifyingGlass size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--chrome-muted)]" />
          <input className="input w-40 py-1.5 pl-8 sm:w-52" placeholder="搜索书名/作者"
                 value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="select py-1.5 text-sm" value={sort}
                onChange={(e) => setSort(e.target.value)}>
          <option value="updated">最近更新</option>
          <option value="created">最近导入</option>
          <option value="title">书名</option>
          <option value="words">字数最多</option>
        </select>
      </div>

      {/* 书卡网格 */}
      {filtered.length === 0 ? (
        <EmptyShelf onImport={() => setShowImport(true)} />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {filtered.map((b, i) => (
            <article key={b.id} className="group rise" style={{ animationDelay: `${i * 40}ms` }}>
              <div className="relative mb-2.5 overflow-hidden rounded-lg shadow-card transition group-hover:-translate-y-1 group-hover:shadow-xl"
                   onClick={() => nav(`/read/${b.id}`)} role="button">
                <img src={api.coverUrl(b.id)} alt={b.title} className="aspect-[3/4.2] w-full cursor-pointer bg-[#e9dfca]" />
                {b.status !== 'want' && (
                  <span className={`absolute left-1.5 top-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLE[b.status]}`}>
                    {STATUS_LABEL[b.status]}
                  </span>
                )}
                <AnalyzeBadge b={b} />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 transition group-hover:opacity-100">
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-white">
                    {b.progress?.percent > 0 ? '继续阅读' : '开始阅读'} <ArrowRight size={13} />
                  </span>
                </div>
              </div>
              <div className="relative">
                <button
                  className="absolute -top-0.5 right-0 rounded-md p-1 text-[var(--chrome-muted)] opacity-70 hover:bg-black/5"
                  onClick={() => setMenuFor(menuFor === b.id ? null : b.id)} aria-label="更多">
                  <DotsThreeVertical size={17} />
                </button>
                {menuFor === b.id && (
                  <div className="fade absolute right-0 top-6 z-20 w-32 overflow-hidden rounded-xl border border-[var(--chrome-border)] bg-white py-1 text-sm shadow-card">
                    <button className="flex w-full items-center gap-2 px-3 py-2 hover:bg-black/5"
                            onClick={() => { setEditing(b); setMenuFor(null) }}>
                      <PencilSimple size={15} /> 编辑信息
                    </button>
                    <button className="flex w-full items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50"
                            onClick={() => del(b)}>
                      <Trash size={15} /> 删除
                    </button>
                  </div>
                )}
                <h3 className="pr-6 truncate text-sm font-semibold">{b.title}</h3>
                <p className="truncate text-xs text-[var(--chrome-muted)]">{b.author || '佚名'}</p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-black/10">
                    <div className="h-full rounded-full bg-[var(--brand-soft)]"
                         style={{ width: `${Math.round((b.progress?.percent || 0) * 100)}%` }} />
                  </div>
                  <span className="text-[10px] text-[var(--chrome-muted)]">
                    {Math.round((b.progress?.percent || 0) * 100)}%
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-[var(--chrome-muted)]">
                  {annCount(b) > 0 ? `${annCount(b)} 条 AI 批注` : b.chapter_count > 0 ? `${b.chapter_count} 章` : ''}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}

      {showImport && <ImportModal onClose={() => setShowImport(false)} onDone={load} />}
      {editing && <BookEditModal book={editing} onClose={() => setEditing(null)} onSaved={load} />}
    </div>
  )
}

function AnalyzeBadge({ b }: { b: Book }) {
  const st = b.analyze?.status
  if (st === 'analyzing') {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-white/85 backdrop-blur-sm">
        <SpinnerGap size={26} className="animate-spin text-[var(--brand)]" />
        <span className="text-xs font-medium text-[var(--brand-deep)]">AI 读书会分析中…</span>
      </div>
    )
  }
  if (st === 'error') {
    return <span className="absolute bottom-1.5 left-1.5 rounded bg-red-600 px-1.5 py-0.5 text-[10px] text-white">分析失败</span>
  }
  if ((b.analyze?.result?.annotations || 0) > 0) {
    return (
      <span className="absolute right-1.5 top-1.5 inline-flex items-center gap-0.5 rounded-full bg-black/55 px-1.5 py-0.5 text-[10px] text-white">
        <Sparkle size={10} weight="fill" /> AI
      </span>
    )
  }
  return null
}

function EmptyShelf({ onImport }: { onImport: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[var(--chrome-border)] bg-white/40 py-20 text-center">
      <CheckCircle size={48} weight="duotone" className="mb-4 text-[var(--brand-soft)] opacity-70" />
      <h3 className="mb-1 text-lg font-semibold">书架还是空的</h3>
      <p className="mb-5 max-w-sm text-sm text-[var(--chrome-muted)]">
        导入一本 TXT / Markdown / EPUB / PDF 小说，六个 AI 角色立刻开始为你做批注、理人物、陪你讨论
      </p>
      <button className="btn btn-primary" onClick={onImport}><Plus size={17} weight="bold" /> 导入第一本书</button>
      <p className="mt-4 text-xs text-[var(--chrome-muted)]">
        预置演示：鲁迅《阿 Q 正传》——运行 seed 即可在书架查看
      </p>
    </div>
  )
}
