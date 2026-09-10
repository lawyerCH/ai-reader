export interface Persona {
  id: string
  name: string
  color: string
  accent_bg: string
  tagline: string
  style: string
}

export interface Book {
  id: number
  title: string
  author: string
  intro: string
  cover: string
  format: string
  status: 'want' | 'reading' | 'finished' | 'dropped'
  tags: string[]
  word_count: number
  chapter_count: number
  created_at: string
  updated_at: string
  last_read_at?: string
  progress: { chapter_idx: number; percent: number; para_idx?: number }
  analyze?: { status: string; result?: Record<string, number>; error?: string }
}

export interface Chapter { idx: number; title: string; word_count: number }
export interface ChapterDetail extends Chapter { paragraphs: string[]; content: string }

export interface Annotation {
  id: number
  book_id: number
  chapter_idx: number
  para_idx: number
  persona: string
  kind: string
  title: string
  content: string
  quote: string
  priority: number
}

export interface Character {
  name: string; aliases: string[]; titles: string[]
  role: 'protagonist' | 'supporting' | 'minor'
  mentions: number; quote_count: number
  first_chapter: number; chapters: number[]
  traits: string[]; emotions: Record<string, number>
  relations: { target: string; weight: number; label: string }[]
  key_events: TimelineEvent[]
  sample_quotes: string[]; importance: number
  profile?: string
}

export interface Relation { source: string; target: string; weight: number; label: string; chapter: number }
export interface TimelineEvent {
  chapter: number; para: number; time: string; title?: string; summary: string; chars: string[]
}
export interface Location { name: string; mentions: number; first_chapter: number; chapters: number[]; desc: string }
export interface Setting { term: string; type: string; mentions: number; first_chapter: number; summary: string }
export interface Foreshadow {
  status: 'planted' | 'resolved'; keyword: string
  plant: { chapter: number; para: number; text: string }
  payoff?: { chapter: number; para: number; text: string } | null
}

export interface Branch {
  id: number; parent_id: number | null; name: string; instruction: string
  scope: string; chapter_idx: number; para_idx: number | null
  content: string; created_at: string; meta?: { plan?: unknown; word_count?: number }
  children?: Branch[]
}

export interface AnswerRef { ch: number; para: number; title: string; text: string }
export interface Answer {
  persona: string; answer: string; intent: string
  refs: AnswerRef[]
  entities: { characters: string[]; locations: string[]; settings: string[] }
}

export interface ReaderSettings {
  theme: string
  fontFamily: string
  fontSize: number
  lineHeight: number
  paraGap: number
  letterSpace: number
  pageMode: 'scroll' | 'paged'
  density: 'dense' | 'normal' | 'sparse' | 'keyonly'
  enabledPersonas: string[]
  autoAnnotations: boolean
}
