import type {
  Book, Chapter, ChapterDetail, Annotation, Character, Relation, TimelineEvent,
  Location, Setting, Foreshadow, Branch, Answer, Persona,
} from './types'

// 同源（本地 dev / 单服务部署）时为 ''；跨域部署时指向独立后端
const API_BASE = (import.meta.env.VITE_API_BASE || '').trim()
const BASE = API_BASE && !/^https?:\/\//.test(API_BASE) ? `https://${API_BASE}` : API_BASE

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  const ct = r.headers.get('content-type') || ''
  return ct.includes('application/json') ? r.json() : (r.text() as unknown as T)
}

export const api = {
  health: () => req<{ ok: boolean; llm: boolean }>('/api/health'),
  personas: () => req<Persona[]>('/api/personas'),

  books: (params = '') => req<Book[]>(`/api/books${params}`),
  book: (id: number) => req<Book>(`/api/books/${id}`),
  patchBook: (id: number, body: Partial<Book>) =>
    req(`/api/books/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteBook: (id: number) => req(`/api/books/${id}`, { method: 'DELETE' }),
  analyze: (id: number) => req(`/api/books/${id}/analyze`),
  reanalyze: (id: number) => req(`/api/books/${id}/reanalyze`, { method: 'POST' }),
  coverUrl: (id: number) => `${BASE}/api/books/${id}/cover`,

  chapters: (id: number) => req<Chapter[]>(`/api/books/${id}/chapters`),
  chapter: (id: number, idx: number) =>
    req<ChapterDetail>(`/api/books/${id}/chapters/${idx}`),

  annotations: (id: number, q: { chapter?: number; density?: string; personas?: string[] } = {}) => {
    const p = new URLSearchParams()
    if (q.chapter !== undefined) p.set('chapter', String(q.chapter))
    if (q.density) p.set('density', q.density)
    if (q.personas?.length) p.set('personas', q.personas.join(','))
    return req<Annotation[]>(`/api/books/${id}/annotations?${p}`)
  },
  annotationStats: (id: number) =>
    req<{ by_persona: Record<string, number>; total: number }>(
      `/api/books/${id}/annotations/stats`),
  digest: (id: number, idx: number) =>
    req<any>(`/api/books/${id}/chapters/${idx}/digest`),

  characters: (id: number) => req<Character[]>(`/api/books/${id}/characters`),
  character: (id: number, name: string) =>
    req<Character>(`/api/books/${id}/characters/${encodeURIComponent(name)}`),
  relations: (id: number) => req<Relation[]>(`/api/books/${id}/relations`),
  timeline: (id: number) => req<TimelineEvent[]>(`/api/books/${id}/timeline`),
  locations: (id: number) => req<Location[]>(`/api/books/${id}/locations`),
  settings: (id: number) => req<Setting[]>(`/api/books/${id}/settings`),
  foreshadows: (id: number) => req<Foreshadow[]>(`/api/books/${id}/foreshadows`),
  recap: (id: number, upto: number) => req<any>(`/api/books/${id}/recap?upto=${upto}`),

  ask: (id: number, body: { q: string; persona?: string; chapter_idx?: number; conversation_id?: number }) =>
    req<Answer>(`/api/books/${id}/ask`, { method: 'POST', body: JSON.stringify(body) }),
  discuss: (id: number, body: { q: string; chapter_idx?: number; personas?: string[] }) =>
    req<{ q: string; answers: Answer[] }>(`/api/books/${id}/discuss`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  debate: (id: number, body: { topic: string; side_a?: string; side_b?: string; chapter_idx?: number }) =>
    req<{ topic: string; turns: { persona: string; content: string }[]; refs: any[] }>(
      `/api/books/${id}/debate`, { method: 'POST', body: JSON.stringify(body) }),
  whatif: (id: number, hypothesis: string) =>
    req<{ hypothesis: string; answers: { persona: string; content: string }[] }>(
      `/api/books/${id}/whatif`, {
        method: 'POST', body: JSON.stringify({ hypothesis }),
      }),
  predict: (id: number) => req<any>(`/api/books/${id}/predict`),

  branches: (id: number) => req<Branch[]>(`/api/books/${id}/branches`),
  branchTree: (id: number) => req<Branch>(`/api/books/${id}/branches/tree`),
  createBranch: (id: number, body: Record<string, unknown>) =>
    req<Branch & { text: string; word_count: number }>(`/api/books/${id}/branches`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  branch: (id: number, brId: number) => req<Branch>(`/api/books/${id}/branches/${brId}`),
  deleteBranch: (id: number, brId: number) =>
    req(`/api/books/${id}/branches/${brId}`, { method: 'DELETE' }),
  materialized: (id: number, brId: number) =>
    req<{ overrides: any[] }>(`/api/books/${id}/branches/${brId}/materialized`),

  progress: {
    get: (id: number) => req<any>(`/api/books/${id}/progress`),
    put: (id: number, body: any) =>
      req(`/api/books/${id}/progress`, { method: 'PUT', body: JSON.stringify(body) }),
  },
  bookmarks: {
    list: (id: number) => req<any[]>(`/api/books/${id}/bookmarks`),
    add: (id: number, body: any) =>
      req<any>(`/api/books/${id}/bookmarks`, { method: 'POST', body: JSON.stringify(body) }),
    del: (id: number, mid: number) =>
      req(`/api/books/${id}/bookmarks/${mid}`, { method: 'DELETE' }),
  },
  highlights: {
    list: (id: number) => req<any[]>(`/api/books/${id}/highlights`),
    add: (id: number, body: any) =>
      req<any>(`/api/books/${id}/highlights`, { method: 'POST', body: JSON.stringify(body) }),
    del: (id: number, hid: number) =>
      req(`/api/books/${id}/highlights/${hid}`, { method: 'DELETE' }),
  },
  session: (id: number, seconds: number, words: number) =>
    req(`/api/books/${id}/sessions`, {
      method: 'POST', body: JSON.stringify({ seconds, words }),
    }),

  statsOverview: () => req<any>('/api/stats/overview'),
  statsBook: (id: number) => req<any>(`/api/stats/books/${id}`),

  readerSettings: {
    get: () => req<any>('/api/settings/reader'),
    put: (settings: unknown) =>
      req('/api/settings/reader', { method: 'PUT', body: JSON.stringify({ settings }) }),
  },
  exportUrl: (id: number, params: string) => `${BASE}/api/books/${id}/export?${params}`,
  qrUrl: (data: string) =>
    `${BASE}/api/qrcode?data=${encodeURIComponent(data)}`,

  async importFiles(files: File[], onProgress?: (n: number) => void): Promise<number[]> {
    const created: number[] = []
    for (const f of files) {
      const fd = new FormData()
      fd.append('files', f)
      const r = await fetch(`${BASE}/api/books/import`, { method: 'POST', body: fd })
      if (!r.ok) throw new Error(await r.text())
      const d = await r.json()
      created.push(...d.created)
      onProgress?.(created.length)
    }
    return created
  },
  importText: (text: string, filename: string, title?: string, author?: string) =>
    req<{ created: number[] }>('/api/books/import/text', {
      method: 'POST', body: JSON.stringify({ text, filename, title, author }),
    }),
}

export function wsUrl(path: string) {
  const proto = BASE.startsWith('https:') || (!BASE && location.protocol === 'https:') ? 'wss' : 'ws'
  const host = BASE ? new URL(BASE).host : location.host
  return `${proto}://${host}${path}`
}
