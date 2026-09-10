import { useRef, useState } from 'react'
import { X, SpinnerGap, PencilSimple, ArrowRight, GitFork } from '@phosphor-icons/react'
import { api, wsUrl } from '../api'
import type { Book } from '../types'

const QUICK = [
  { label: '改成好结局（HE）', text: '我不喜欢这个结局，让主角活下来、沉冤得雪，给一个温暖的好结局' },
  { label: '主角复仇成功', text: '让主角复仇成功，所有欺辱过他的人都付出代价' },
  { label: 'CP 在一起', text: '让主角和心上人终成眷属' },
  { label: '反派黑化', text: '把这个人彻底黑化成幕后大反派' },
  { label: '悲剧收场（BE）', text: '改成更彻底的悲剧结局，所有人都没能被拯救' },
]
const SCOPES = [
  ['paragraph', '段落'], ['chapter', '章节'], ['ending', '结局'], ['full', '全篇'],
] as const

export default function RewriteSheet({
  book, chapterIdx, paraIdx, selectedText, open, onClose, onReadBranch,
}: {
  book: Book
  chapterIdx: number
  paraIdx: number | null
  selectedText: string
  open: boolean
  onClose: () => void
  onReadBranch: (id: number, name: string) => void
}) {
  if (!open) return null
  const [scope, setScope] = useState<(typeof SCOPES)[number][0]>(
    selectedText ? 'paragraph' : 'ending')
  const [instruction, setInstruction] = useState('')
  const [name, setName] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [output, setOutput] = useState('')
  const [plan, setPlan] = useState<any>(null)
  const [branchId, setBranchId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  function run() {
    if (!instruction.trim() || streaming) return
    setStreaming(true); setOutput(''); setPlan(null); setBranchId(null); setError('')
    const ws = new WebSocket(wsUrl(`/ws/rewrite/${book.id}`))
    wsRef.current = ws
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data)
      if (m.event === 'plan') setPlan(m.plan)
      if (m.event === 'delta') setOutput((o) => o + m.delta)
      if (m.event === 'done') {
        setBranchId(m.branch_id)
        setStreaming(false)
        ws.close()
      }
      if (m.event === 'error') { setError(m.message || '生成失败'); setStreaming(false) }
    }
    ws.onerror = () => setError('连接失败，请确认后端已启动')
    ws.onopen = () => ws.send(JSON.stringify({
      scope,
      chapter_idx: chapterIdx,
      para_idx: paraIdx,
      original_text: selectedText,
      instruction: instruction.trim(),
      name: name || '我的改写',
    }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 fade sm:items-center" onClick={onClose}>
      <div className="pop flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl bg-[var(--chrome-panel)] sm:rounded-2xl"
           onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center gap-2 border-b border-[var(--chrome-border)] px-5 py-3.5">
          <PencilSimple size={19} className="text-[var(--brand)]" />
          <div>
            <h2 className="text-base font-bold">读者分支 · 一句话改写</h2>
            <p className="text-[11px] text-[var(--chrome-muted)]">
              当前位置：第{chapterIdx + 1}章{selectedText ? '·段落' : ''}，生成后保存为新分支，原版不受影响
            </p>
          </div>
          <button className="icon-btn ml-auto" onClick={onClose}><X size={19} /></button>
        </header>

        <div className="scroll-area space-y-3 overflow-y-auto p-5">
          <div className="flex gap-1.5">
            {SCOPES.map(([k, l]) => (
              <button key={k} disabled={k === 'paragraph' && !selectedText}
                className={`chip flex-1 justify-center disabled:opacity-40 ${scope === k ? 'on' : ''}`}
                onClick={() => setScope(k)}>{l}</button>
            ))}
          </div>

          <input className="input" placeholder="分支名称（如：阿Q活下来了）" value={name}
                 onChange={(e) => setName(e.target.value)} />

          <textarea className="input h-24 resize-none"
            placeholder="用一句话说出你想要的故事，例如：让主角赢、两个人在一起、把结局改成悲剧…"
            value={instruction} onChange={(e) => setInstruction(e.target.value)} />

          <div className="flex flex-wrap gap-1.5">
            {QUICK.map((q) => (
              <button key={q.label} className="chip text-[11px]" onClick={() => setInstruction(q.text)}>
                {q.label}
              </button>
            ))}
          </div>

          {plan && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
              AI 识别意图：{(plan.intents || []).join('、') || '自定义改写'}
              {plan.targets?.length > 0 && ` · 相关人物：${plan.targets.slice(0, 4).join('、')}`}
            </div>
          )}

          {output && (
            <article className="reader-surface rounded-xl p-4" data-theme="paper">
              <div className="book-content text-[15px]" style={{ ['--r-font-size' as any]: '16px' }}>
                {output.split('\n').filter(Boolean).map((p, i) => {
                  if (p.startsWith('【')) return <h3 key={i} className="text-center font-bold">{p.replace(/[【】]/g, '')}</h3>
                  return <p key={i} className="para">{p}</p>
                })}
              </div>
            </article>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <footer className="flex items-center gap-2 border-t border-[var(--chrome-border)] px-5 py-3">
          <button className="btn btn-primary" disabled={streaming || !instruction.trim()} onClick={run}>
            {streaming ? <SpinnerGap size={16} className="animate-spin" /> : <PencilSimple size={16} />}
            {streaming ? 'AI 正在奋笔疾书…' : '生成改写'}
          </button>
          {branchId && (
            <button className="btn" style={{ background: '#0F766E', color: '#fff' }}
              onClick={() => onReadBranch(branchId, name || '我的改写')}>
              <GitFork size={16} /> 立即阅读此分支 <ArrowRight size={14} />
            </button>
          )}
          <span className="ml-auto text-[11px] text-[var(--chrome-muted)]">
            {output ? `已生成 ${output.length} 字` : ''}
          </span>
        </footer>
      </div>
    </div>
  )
}
