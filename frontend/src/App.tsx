import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Books, ChartLineUp, BookOpenText } from '@phosphor-icons/react'
import Bookshelf from './pages/Bookshelf'
import Reader from './pages/Reader'
import Dashboard from './pages/Dashboard'
import { useUiStore } from './store'

export default function App() {
  const loc = useLocation()
  const toast = useUiStore((s) => s.toast)
  const inReader = loc.pathname.startsWith('/read/')

  if (inReader) {
    return (
      <>
        <Routes>
          <Route path="/read/:id" element={<Reader />} />
        </Routes>
        {toast && <div className="fixed left-1/2 top-4 z-[100] -translate-x-1/2 rounded-full bg-black/80 px-4 py-2 text-sm text-white fade">{toast}</div>}
      </>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-[var(--chrome-border)] bg-[var(--chrome-panel)]/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
          <BookOpenText size={26} weight="duotone" color="var(--brand)" />
          <div className="leading-tight">
            <div className="text-[15px] font-bold tracking-wide">AI 读书会</div>
            <div className="text-[11px] text-[var(--chrome-muted)]">AI 陪你看小说，还能帮你改小说</div>
          </div>
          <nav className="ml-auto hidden items-center gap-1 sm:flex">
            <TopLink to="/" icon={<Books size={18} />} label="书架" />
            <TopLink to="/stats" icon={<ChartLineUp size={18} />} label="数据看板" />
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-5 sm:pb-10">
        <Routes>
          <Route path="/" element={<Bookshelf />} />
          <Route path="/stats" element={<Dashboard />} />
        </Routes>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--chrome-border)] bg-[var(--chrome-panel)]/95 backdrop-blur sm:hidden safe-bottom">
        <div className="mx-auto flex max-w-md">
          <Tab to="/" icon={<Books size={22} />} label="书架" />
          <Tab to="/stats" icon={<ChartLineUp size={22} />} label="看板" />
        </div>
      </nav>

      {toast && (
        <div className="fixed left-1/2 top-4 z-[100] -translate-x-1/2 rounded-full bg-black/80 px-4 py-2 text-sm text-white fade">
          {toast}
        </div>
      )}
    </div>
  )
}

function TopLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink to={to} end
      className={({ isActive }) =>
        `btn ${isActive ? 'bg-[rgba(138,90,36,.12)] text-[var(--brand-deep)]' : 'text-[var(--chrome-muted)]'}`}>
      {icon}{label}
    </NavLink>
  )
}

function Tab({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink to={to} end className={({ isActive }) =>
      `flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] ${
        isActive ? 'text-[var(--brand)]' : 'text-[var(--chrome-muted)]'}`}>
      {icon}{label}
    </NavLink>
  )
}
