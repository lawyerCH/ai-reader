import { useEffect, useState } from 'react'
import { X, GitFork, BookOpen } from '@phosphor-icons/react'
import { api } from '../api'
import type { Book } from '../types'

interface TreeNode {
  id: number
  name: string
  scope?: string
  chapter_idx?: number
  instruction?: string
  children?: TreeNode[]
}

export default function BranchTreeModal({
  book, activeId, open, onPick, onClose,
}: {
  book: Book
  activeId: number | null
  open: boolean
  onPick: (id: number | null, name?: string) => void
  onClose: () => void
}) {
  const [tree, setTree] = useState<TreeNode | null>(null)
  useEffect(() => { if (open) api.branchTree(book.id).then(setTree as any) }, [book.id, open])
  if (!open) return null

  function NodeView({ n, depth }: { n: TreeNode; depth: number }) {
    const isRoot = n.id === 0
    const active = activeId === n.id || (!activeId && isRoot)
    return (
      <div style={{ marginLeft: depth * 22 }}>
        <button onClick={() => onPick(isRoot ? null : n.id, n.name)}
          className={`mb-1.5 flex w-full items-start gap-2 rounded-xl border p-2.5 text-left transition ${
            active ? 'border-[var(--brand)] bg-amber-50' : 'border-[var(--chrome-border)] bg-white hover:shadow-sm'}`}>
          {isRoot ? <BookOpen size={18} className="mt-0.5 text-[var(--brand)]" />
                  : <GitFork size={18} className="mt-0.5 text-[var(--brand)]" />}
          <span className="min-w-0">
            <span className="block text-sm font-semibold">{n.name}</span>
            {n.instruction && <span className="line-clamp-2 block text-[11px] text-[var(--chrome-muted)]">{n.instruction}</span>}
            {n.scope && n.scope !== 'original' && (
              <span className="mt-0.5 inline-block rounded bg-black/5 px-1.5 text-[10px] text-[var(--chrome-muted)]">
                第{(n.chapter_idx ?? 0) + 1}章 · {n.scope}
              </span>
            )}
            {active && <span className="ml-1 text-[10px] font-bold text-[var(--brand)]">阅读中</span>}
          </span>
        </button>
        {n.children?.map((c) => <NodeView key={c.id} n={c} depth={depth + 1} />)}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 fade p-4" onClick={onClose}>
      <div className="pop chrome-card max-h-[82vh] w-full max-w-xl overflow-hidden rounded-2xl"
           onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-[var(--chrome-border)] px-5 py-3">
          <h2 className="flex items-center gap-2 text-base font-bold"><GitFork className="text-[var(--brand)]" size={19} /> 分支树</h2>
          <button className="icon-btn" onClick={onClose}><X size={19} /></button>
        </header>
        <div className="scroll-area max-h-[70vh] overflow-y-auto p-4">
          {tree ? <NodeView n={tree} depth={0} /> : <p className="py-8 text-center text-sm text-[var(--chrome-muted)]">加载中…</p>}
        </div>
      </div>
    </div>
  )
}
