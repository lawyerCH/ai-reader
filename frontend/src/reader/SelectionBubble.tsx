import { ChatCircleText, PencilSimple, ShareNetwork, BookmarkSimple, HighlighterCircle } from '@phosphor-icons/react'

const COLORS = [
  { id: 'yellow', hex: '#eab308' },
  { id: 'green', hex: '#22c55e' },
  { id: 'blue', hex: '#3b82f6' },
  { id: 'pink', hex: '#ec4899' },
  { id: 'orange', hex: '#f97316' },
]

export interface SelectionTarget {
  text: string
  chapterIdx: number
  paraIdx: number
  startOffset?: number
  rect: { x: number; y: number; w: number }
}

export default function SelectionBubble({
  target, onHighlight, onAsk, onRewrite, onPoster, onBookmark, onClose,
}: {
  target: SelectionTarget
  onHighlight: (color: string) => void
  onAsk: () => void
  onRewrite: () => void
  onPoster: () => void
  onBookmark: () => void
  onClose: () => void
}) {
  const { x, y, w } = target.rect
  const left = Math.max(8, Math.min(x + w / 2 - 168, window.innerWidth - 344))
  const top = Math.max(56, y - 52)
  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="pop fixed z-50 flex items-center gap-1 rounded-2xl bg-[#2b2620] px-2 py-1.5 text-white shadow-2xl"
           style={{ left, top }}>
        <HighlighterCircle size={16} className="ml-1 opacity-70" />
        {COLORS.map((c) => (
          <button key={c.id} title={`${c.id}色高亮`}
            className="mx-0.5 h-5 w-5 rounded-full border border-white/40 transition hover:scale-115"
            style={{ background: c.hex }} onClick={() => onHighlight(c.id)} />
        ))}
        <span className="mx-1 h-5 w-px bg-white/25" />
        <Tool icon={<ChatCircleText size={17} />} label="问 AI" onClick={onAsk} />
        <Tool icon={<PencilSimple size={17} />} label="改写" onClick={onRewrite} />
        <Tool icon={<ShareNetwork size={17} />} label="金句" onClick={onPoster} />
        <Tool icon={<BookmarkSimple size={17} />} label="书签" onClick={onBookmark} />
      </div>
    </>
  )
}

function Tool({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-[10px] hover:bg-white/15">
      {icon}<span>{label}</span>
    </button>
  )
}
