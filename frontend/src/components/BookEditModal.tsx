import { useState } from 'react'
import { X } from '@phosphor-icons/react'
import { api } from '../api'
import type { Book } from '../types'

export default function BookEditModal({ book, onClose, onSaved }:
  { book: Book; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(book.title)
  const [author, setAuthor] = useState(book.author)
  const [intro, setIntro] = useState(book.intro)
  const [tags, setTags] = useState((book.tags || []).join('、'))
  const [status, setStatus] = useState(book.status)
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    await api.patchBook(book.id, {
      title, author, intro, status: status as Book['status'],
      tags: tags.split(/[、,\s]+/).filter(Boolean) as string[],
    })
    onSaved(); onClose()
  }

  const statuses = [
    ['want', '想读'], ['reading', '在读'], ['finished', '已读'], ['dropped', '搁置'],
  ] as const

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 fade sm:items-center" onClick={onClose}>
      <div className="pop chrome-card w-full max-w-lg rounded-b-none p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">书籍信息</h2>
          <button className="icon-btn" onClick={onClose} aria-label="关闭"><X size={20} /></button>
        </div>
        <div className="space-y-3">
          <div className="flex gap-3">
            <label className="flex-1 text-sm">
              <span className="mb-1 block text-[var(--chrome-muted)]">书名</span>
              <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label className="flex-1 text-sm">
              <span className="mb-1 block text-[var(--chrome-muted)]">作者</span>
              <input className="input" value={author} onChange={(e) => setAuthor(e.target.value)} />
            </label>
          </div>
          <label className="block text-sm">
            <span className="mb-1 block text-[var(--chrome-muted)]">简介</span>
            <textarea className="input h-24 resize-none" value={intro} onChange={(e) => setIntro(e.target.value)} />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-[var(--chrome-muted)]">标签（、分隔）</span>
            <input className="input" value={tags} onChange={(e) => setTags(e.target.value)} />
          </label>
          <div className="text-sm">
            <span className="mb-1 block text-[var(--chrome-muted)]">状态</span>
            <div className="flex gap-2">
              {statuses.map(([k, l]) => (
                <button key={k} className={`chip ${status === k ? 'on' : ''}`} onClick={() => setStatus(k)}>{l}</button>
              ))}
            </div>
          </div>
          <button className="btn btn-primary w-full" disabled={busy} onClick={save}>保存</button>
        </div>
      </div>
    </div>
  )
}
