import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts'
import {
  Books, ClockCountdown, PencilLine, Sparkle, ChatCircleDots,
  GitFork, DownloadSimple, Trophy,
} from '@phosphor-icons/react'
import { api } from '../api'
import { PersonaAvatar, DEFAULT_COLORS, PERSONA_LABEL } from '../components/PersonaAvatar'

export default function Dashboard() {
  const nav = useNavigate()
  const [s, setS] = useState<any>(null)
  const [books, setBooks] = useState<any[]>([])

  useEffect(() => {
    api.statsOverview().then(setS)
    api.books().then(setBooks)
  }, [])

  if (!s) return <p className="py-16 text-center text-sm text-[var(--chrome-muted)]">统计中…</p>

  const daily = (s.daily || []).map((d: any) => ({
    day: d.day.slice(5),
    minutes: Math.round(d.seconds / 60),
    words: d.words,
  }))
  const personaData = Object.entries(s.annotation_by_persona || {})
    .map(([k, v]) => ({ name: PERSONA_LABEL[k] || k, id: k, count: v as number }))
    .sort((a, b) => b.count - a.count)

  const cards = [
    { icon: <Books size={22} />, label: '藏书', value: s.book_count, sub: `在读 ${s.reading_count} · 读完 ${s.finished_count}` },
    { icon: <ClockCountdown size={22} />, label: '总阅读时长', value: `${Math.round(s.total_seconds / 3600 * 10) / 10}h`, sub: `${s.active_days} 个活跃日` },
    { icon: <PencilLine size={22} />, label: '已读字数', value: `${Math.round(s.words_read / 10000 * 10) / 10}万`, sub: `藏书 ${(s.total_words / 10000).toFixed(1)} 万字` },
    { icon: <Sparkle size={22} />, label: 'AI 批注', value: Object.values(s.annotation_by_persona).reduce((a: number, b) => a + (b as number), 0), sub: '六角色陪读产出' },
    { icon: <GitFork size={22} />, label: '读者分支', value: s.branch_count, sub: `改写约 ${Math.round(s.branch_words / 1000)}k 字` },
  ]

  return (
    <div className="rise space-y-5">
      <h1 className="font-serif text-2xl font-bold">阅读数据看板</h1>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="chrome-card p-4">
            <div className="mb-2 inline-flex text-[var(--brand)]">{c.icon}</div>
            <div className="text-2xl font-bold tabular-nums">{c.value}</div>
            <div className="text-xs font-medium">{c.label}</div>
            <div className="mt-0.5 text-[10px] text-[var(--chrome-muted)]">{c.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="chrome-card p-4">
          <h3 className="mb-3 text-sm font-bold">最近阅读时长（分钟/天）</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={daily}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#d97706" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#d97706" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" fontSize={10} interval={2} />
              <YAxis fontSize={10} />
              <Tooltip formatter={(v: any) => `${v} 分钟`} />
              <Area type="monotone" dataKey="minutes" stroke="#d97706" strokeWidth={2} fill="url(#g1)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chrome-card p-4">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-bold">
            <ChatCircleDots size={16} className="text-[var(--brand)]" /> 最爱和哪位 AI 互动
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={personaData} layout="vertical" margin={{ left: 20 }}>
              <XAxis type="number" fontSize={10} />
              <YAxis type="category" dataKey="name" fontSize={11} width={76} />
              <Tooltip />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {personaData.map((d) => <Cell key={d.id} fill={DEFAULT_COLORS[d.id] || '#b45309'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap gap-2">
            {personaData.map((d) => (
              <span key={d.id} className="inline-flex items-center gap-1 rounded-full bg-black/5 px-2 py-0.5 text-[11px]">
                <PersonaAvatar persona={d.id} color={DEFAULT_COLORS[d.id]} size={16} />
                {d.count} 条
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="chrome-card p-4">
        <h3 className="mb-3 flex items-center gap-1.5 text-sm font-bold">
          <Trophy size={16} className="text-[var(--brand)]" /> 我的书
        </h3>
        <div className="space-y-2">
          {books.map((b) => (
            <div key={b.id} className="flex items-center gap-3 rounded-xl border border-[var(--chrome-border)] bg-white/60 p-2.5">
              <img src={api.coverUrl(b.id)} alt="" className="h-14 w-10 rounded shadow" onClick={() => nav(`/read/${b.id}`)} role="button" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold">{b.title}</div>
                <div className="text-[11px] text-[var(--chrome-muted)]">
                  {b.author || '佚名'} · {b.chapter_count} 章 · {b.word_count.toLocaleString()} 字
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded bg-black/10">
                  <div className="h-full bg-[var(--brand-soft)]" style={{ width: `${Math.round((b.progress?.percent || 0) * 100)}%` }} />
                </div>
              </div>
              <a className="btn btn-ghost px-2.5 py-1.5 text-xs"
                 href={api.exportUrl(b.id, 'type=notes&format=markdown')}
                 download><DownloadSimple size={14} /> 笔记</a>
              <a className="btn btn-ghost px-2.5 py-1.5 text-xs"
                 href={api.exportUrl(b.id, 'type=report&format=markdown')}
                 download><DownloadSimple size={14} /> 报告</a>
              <button className="btn btn-ghost px-2.5 py-1.5 text-xs"
                      onClick={() => nav(`/read/${b.id}`)}><PencilLine size={14} /> 续读</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
