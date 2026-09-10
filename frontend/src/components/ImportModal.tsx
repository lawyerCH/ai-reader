import { useState } from 'react'
import { X, FileText, SpinnerGap, UploadSimple } from '@phosphor-icons/react'
import { api } from '../api'
import { useUiStore } from '../store'

export default function ImportModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [tab, setTab] = useState<'file' | 'text'>('file')
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const showToast = useUiStore((s) => s.showToast)

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).filter((f) =>
      /\.(txt|md|markdown|epub|pdf)$/i.test(f.name))
    if (!list.length) {
      showToast('支持 TXT / Markdown / EPUB / PDF')
      return
    }
    setBusy(true)
    try {
      const ids = await api.importFiles(list)
      showToast(`已导入 ${ids.length} 本，AI 读书会开始工作…`)
      onDone()
      onClose()
    } catch (e: any) {
      showToast('导入失败：' + e.message)
    } finally {
      setBusy(false)
    }
  }

  async function submitText() {
    if (text.trim().length < 20) return showToast('正文太短了，至少贴入几十字吧')
    setBusy(true)
    try {
      await api.importText(text, (title || '粘贴小说') + '.txt', title || undefined, author || undefined)
      showToast('导入成功，AI 正在分析…')
      onDone(); onClose()
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 fade sm:items-center"
         onClick={onClose}>
      <div className="pop chrome-card w-full max-w-lg rounded-b-none p-5 sm:rounded-2xl"
           onClick={(e) => e.stopPropagation()}
           onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
           onDragLeave={() => setDrag(false)}
           onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files) }}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">导入小说</h2>
          <button className="icon-btn" onClick={onClose} aria-label="关闭"><X size={20} /></button>
        </div>

        <div className="mb-4 flex gap-1 rounded-xl bg-black/5 p-1">
          {(['file', 'text'] as const).map((t) => (
            <button key={t}
              className={`flex-1 rounded-lg py-2 text-sm font-medium ${tab === t ? 'bg-white shadow-sm' : 'text-[var(--chrome-muted)]'}`}
              onClick={() => setTab(t)}>
              {t === 'file' ? '文件导入' : '粘贴文本'}
            </button>
          ))}
        </div>

        {tab === 'file' ? (
          <label
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
              drag ? 'border-[var(--brand)] bg-[rgba(217,119,6,.08)]' : 'border-[var(--chrome-border)] bg-black/[.02]'}`}>
            {busy
              ? <SpinnerGap size={34} className="animate-spin text-[var(--brand)]" />
              : <UploadSimple size={34} weight="duotone" className="text-[var(--brand)]" />}
            <div className="text-sm font-medium">
              {busy ? '正在导入并分析…' : '点击选择，或把文件拖到这里'}
            </div>
            <div className="text-xs text-[var(--chrome-muted)]">
              支持 TXT / Markdown / EPUB / PDF，可一次选择多本
            </div>
            <input type="file" multiple accept=".txt,.md,.markdown,.epub,.pdf" hidden
                   onChange={(e) => e.target.files && handleFiles(e.target.files)} />
          </label>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input className="input" placeholder="书名（可选）" value={title} onChange={(e) => setTitle(e.target.value)} />
              <input className="input" placeholder="作者（可选）" value={author} onChange={(e) => setAuthor(e.target.value)} />
            </div>
            <textarea className="input h-52 resize-none" placeholder="把小说全文粘贴到这里…" value={text} onChange={(e) => setText(e.target.value)} />
            <button className="btn btn-primary w-full" disabled={busy} onClick={submitText}>
              {busy ? <SpinnerGap className="animate-spin" size={16} /> : <FileText size={16} />}
              导入并开始 AI 分析
            </button>
          </div>
        )}
        <p className="mt-3 text-center text-xs text-[var(--chrome-muted)]">
          导入即自动完成章节切分、人物图谱与六角色批注，零配置
        </p>
      </div>
    </div>
  )
}
