import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ReaderSettings } from './types'

export const FONT_FAMILIES = [
  { id: 'serif-sc', label: '思源宋体', css: '"Noto Serif SC", Songti SC, STSong, SimSun, serif' },
  { id: 'song', label: '经典宋体', css: 'Songti SC, STSong, SimSun, "Noto Serif SC", serif' },
  { id: 'hei', label: '思源黑体', css: '"Noto Sans SC", PingFang SC, "Microsoft YaHei", sans-serif' },
  { id: 'kai', label: '楷体', css: 'KaiTi, STKaiti, "Kaiti SC", "Noto Serif SC", serif' },
  { id: 'ming', label: '明朝体', css: '"Noto Serif SC", "Songti SC", "Hiragino Mincho ProN", serif' },
  { id: 'round', label: '圆体', css: '"Yuanti SC", "YouYuan", "PingFang SC", sans-serif' },
]

export const READER_THEMES = [
  { id: 'paper', name: '米白', swatch: '#f6efe0', dark: false },
  { id: 'white', name: '雪白', swatch: '#ffffff', dark: false },
  { id: 'parchment', name: '羊皮纸', swatch: '#ecddbd', dark: false },
  { id: 'green', name: '护眼绿', swatch: '#dfe8d6', dark: false },
  { id: 'blue', name: '淡蓝', swatch: '#e3ecf4', dark: false },
  { id: 'pink', name: '樱花粉', swatch: '#f7e9ee', dark: false },
  { id: 'gray', name: '灰墨', swatch: '#e5e3df', dark: false },
  { id: 'sepia-night', name: '夜间棕', swatch: '#211a12', dark: true },
  { id: 'dark', name: '深夜灰', swatch: '#14161b', dark: true },
  { id: 'amoled', name: '纯黑', swatch: '#000000', dark: true },
]

const defaultSettings: ReaderSettings = {
  theme: 'paper',
  fontFamily: 'serif-sc',
  fontSize: 20,
  lineHeight: 1.9,
  paraGap: 1.15,
  letterSpace: 0.02,
  pageMode: 'scroll',
  density: 'normal',
  enabledPersonas: ['plot', 'lore', 'emotion', 'snark', 'professor', 'character'],
  autoAnnotations: true,
}

interface ReaderState {
  settings: ReaderSettings
  set: (patch: Partial<ReaderSettings>) => void
  togglePersona: (id: string) => void
  reset: () => void
}

export const useReaderStore = create<ReaderState>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      set: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
      togglePersona: (id) =>
        set((s) => {
          const has = s.settings.enabledPersonas.includes(id)
          return {
            settings: {
              ...s.settings,
              enabledPersonas: has
                ? s.settings.enabledPersonas.filter((p) => p !== id)
                : [...s.settings.enabledPersonas, id],
            },
          }
        }),
      reset: () => set({ settings: defaultSettings }),
    }),
    { name: 'ai-reader-settings' },
  ),
)

interface UiState {
  importing: boolean
  setImporting: (v: boolean) => void
  toast: string | null
  showToast: (t: string) => void
}
export const useUiStore = create<UiState>((set) => ({
  importing: false,
  setImporting: (v) => set({ importing: v }),
  toast: null,
  showToast: (t) => {
    set({ toast: t })
    setTimeout(() => set({ toast: null }), 2600)
  },
}))
