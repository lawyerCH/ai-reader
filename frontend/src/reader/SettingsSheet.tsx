import { X, Sun, Moon, Article, Scroll, ListChecks } from '@phosphor-icons/react'
import { FONT_FAMILIES, READER_THEMES, useReaderStore } from '../store'
import { PersonaAvatar, DEFAULT_COLORS } from '../components/PersonaAvatar'
import { api } from '../api'
import { useEffect } from 'react'

const PERSONA_IDS = ['plot', 'lore', 'emotion', 'snark', 'professor', 'character']

function Slider({ label, value, min, max, step, unit = '', onChange }:
  { label: string; value: number; min: number; max: number; step: number; unit?: string; onChange: (v: number) => void }) {
  return (
    <label className="block py-1.5">
      <div className="mb-1 flex justify-between text-xs text-[var(--chrome-muted)]">
        <span>{label}</span><span className="tabular-nums">{value}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--brand)]" />
    </label>
  )
}

export default function SettingsSheet({ open, onClose, bookId }:
  { open: boolean; onClose: () => void; bookId: number }) {
  const { settings, set, togglePersona } = useReaderStore()
  useEffect(() => {
    if (open) api.readerSettings.put(settings).catch(() => {})
  }, [settings, open])

  if (!open) return null
  const isDark = READER_THEMES.find((t) => t.id === settings.theme)?.dark
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/35 fade" onClick={onClose}>
      <aside className="scroll-area h-full w-[88vw] max-w-sm overflow-y-auto bg-[var(--chrome-panel)] p-5 shadow-sheet pop"
             onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-bold">阅读设置</h2>
          <button className="icon-btn" onClick={onClose}><X size={19} /></button>
        </div>

        <Section icon={<Sun size={16} />} title="背景主题">
          <div className="grid grid-cols-5 gap-2">
            {READER_THEMES.map((t) => (
              <button key={t.id} title={t.name} onClick={() => set({ theme: t.id })}
                className={`relative aspect-square rounded-lg border-2 transition ${settings.theme === t.id ? 'border-[var(--brand)]' : 'border-black/10'}`}
                style={{ background: t.swatch }}>
                <span className="absolute inset-x-0 bottom-0.5 text-center text-[9px]"
                      style={{ color: t.dark ? '#ddd' : '#555' }}>{t.name}</span>
                {t.dark && <Moon size={9} className="absolute right-1 top-1" color="#aaa" />}
              </button>
            ))}
          </div>
        </Section>

        <Section icon={<Article size={16} />} title="字体（5 种以上）">
          <div className="grid grid-cols-2 gap-1.5">
            {FONT_FAMILIES.map((f) => (
              <button key={f.id} className={`chip justify-center ${settings.fontFamily === f.id ? 'on' : ''}`}
                style={{ fontFamily: f.css }}
                onClick={() => set({ fontFamily: f.id })}>
                {f.label}
              </button>
            ))}
          </div>
        </Section>

        <Section icon={<Scroll size={16} />} title="字号与间距（无极调节）">
          <Slider label="字号" value={settings.fontSize} min={15} max={30} step={1} unit="px"
                  onChange={(v) => set({ fontSize: v })} />
          <Slider label="行间距" value={settings.lineHeight} min={1.4} max={2.6} step={0.05}
                  onChange={(v) => set({ lineHeight: v })} />
          <Slider label="段间距" value={settings.paraGap} min={0.4} max={2.6} step={0.05} unit="em"
                  onChange={(v) => set({ paraGap: v })} />
          <Slider label="字间距" value={settings.letterSpace} min={0} max={0.12} step={0.005} unit="em"
                  onChange={(v) => set({ letterSpace: v })} />
        </Section>

        <Section title="翻页模式">
          <div className="flex gap-2">
            {([['scroll', '连续滚动'], ['paged', '仿真翻页']] as const).map(([k, l]) => (
              <button key={k} className={`chip ${settings.pageMode === k ? 'on' : ''}`}
                      onClick={() => set({ pageMode: k })}>{l}</button>
            ))}
          </div>
        </Section>

        <Section title="批注密度">
          <div className="grid grid-cols-4 gap-1.5">
            {([['dense', '密集'], ['normal', '适中'], ['sparse', '稀疏'], ['keyonly', '仅关键']] as const).map(
              ([k, l]) => (
                <button key={k} className={`chip justify-center ${settings.density === k ? 'on' : ''}`}
                  onClick={() => set({ density: k })}>{l}</button>
              ))}
          </div>
        </Section>

        <Section icon={<ListChecks size={16} />} title="陪读阵容（点击开关 AI 角色）">
          <div className="space-y-1.5">
            {PERSONA_IDS.map((id) => {
              const on = settings.enabledPersonas.includes(id)
              return (
                <button key={id} onClick={() => togglePersona(id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left transition ${
                    on ? 'border-[var(--chrome-border)] bg-white' : 'border-transparent bg-black/5 opacity-50'}`}>
                  <PersonaAvatar persona={id} color={DEFAULT_COLORS[id]} size={26} />
                  <span className="text-sm font-medium">{({
                    plot: '剧情党', lore: '考据党', emotion: '情感分析师',
                    snark: '吐槽君', professor: '文学教授', character: '角色本人',
                  } as Record<string, string>)[id]}</span>
                  <span className={`ml-auto h-5 w-9 rounded-full p-0.5 transition ${on ? 'bg-[var(--brand)]' : 'bg-black/15'}`}>
                    <span className={`block h-4 w-4 rounded-full bg-white transition ${on ? 'translate-x-4' : ''}`} />
                  </span>
                </button>
              )
            })}
          </div>
        </Section>
      </aside>
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[var(--chrome-muted)]">
        {icon}{title}
      </h3>
      {children}
    </section>
  )
}
