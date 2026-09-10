import { useEffect, useMemo, useRef, useState } from 'react'
import type { Character, Relation } from '../types'

interface Node {
  name: string
  x: number; y: number
  vx: number; vy: number
  r: number
  role: string
  importance: number
}

const EDGE_COLOR: Record<string, string> = {
  冲突: '#DC4F3B', 仇敌: '#DC4F3B',
  爱慕: '#DB4A8D', 妻子: '#DB4A8D', 丈夫: '#DB4A8D',
  父亲: '#2563EB', 母亲: '#2563EB', 儿子: '#2563EB', 女儿: '#2563EB',
  师父: '#7C3AED', 徒弟: '#7C3AED', 同门: '#7C3AED',
  朋友: '#0F766E',
}

export default function CharacterGraph({
  characters, relations, onSelect, max = 18,
}: {
  characters: Character[]
  relations: Relation[]
  onSelect?: (name: string) => void
  max?: number
}) {
  const ref = useRef<SVGSVGElement>(null)
  const [size, setSize] = useState({ w: 420, h: 460 })
  const [tick, setTick] = useState(0)
  const nodesRef = useRef<Node[]>([])

  const topChars = useMemo(() => {
    const picked = characters.filter((c) => c.role !== 'minor').slice(0, max)
    const rest = characters.filter((c) => c.role === 'minor').slice(0, Math.max(0, max - picked.length))
    return [...picked, ...rest]
  }, [characters, max])

  const edges = useMemo(() => relations.filter((e) =>
    topChars.some((c) => c.name === e.source) &&
    topChars.some((c) => c.name === e.target)).slice(0, 46),
    [relations, topChars])

  useEffect(() => {
    const el = ref.current?.parentElement
    if (!el) return
    const ro = new ResizeObserver(() => {
      setSize({ w: el.clientWidth || 420, h: Math.max(380, el.clientHeight || 460) })
    })
    ro.observe(el)
    setSize({ w: el.clientWidth || 420, h: Math.max(380, el.clientHeight || 460) })
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const cx = size.w / 2, cy = size.h / 2
    const nodes: Node[] = topChars.map((c, i) => {
      const a = (i / Math.max(1, topChars.length)) * Math.PI * 2
      const ring = c.role === 'protagonist' ? 0 : c.role === 'supporting' ? 90 : 170
      return {
        name: c.name,
        x: cx + Math.cos(a) * ring + (Math.sin(i * 3) * 18),
        y: cy + Math.sin(a) * ring + (Math.cos(i * 2) * 18),
        vx: 0, vy: 0,
        r: c.role === 'protagonist' ? 26 : c.role === 'supporting' ? 18 : 13,
        role: c.role, importance: c.importance,
      }
    })
    nodesRef.current = nodes
    const byName = new Map(nodes.map((n) => [n.name, n]))

    let raf = 0
    let t = 0
    const step = () => {
      t += 1
      // 斥力
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          let dx = nodes[i].x - nodes[j].x
          let dy = nodes[i].y - nodes[j].y
          let d2 = dx * dx + dy * dy || 1
          const f = 2600 / d2
          const d = Math.sqrt(d2)
          dx /= d; dy /= d
          nodes[i].vx += dx * f; nodes[i].vy += dy * f
          nodes[j].vx -= dx * f; nodes[j].vy -= dy * f
        }
      }
      // 弹簧
      for (const e of edges) {
        const a = byName.get(e.source), b = byName.get(e.target)
        if (!a || !b) continue
        const dx = b.x - a.x, dy = b.y - a.y
        const d = Math.hypot(dx, dy) || 1
        const target = 60 + (3 - Math.min(3, e.weight)) * 18
        const f = (d - target) * 0.02
        a.vx += (dx / d) * f * e.weight; a.vy += (dy / d) * f * e.weight
        b.vx -= (dx / d) * f * e.weight; b.vy -= (dy / d) * f * e.weight
      }
      // 向心 & 阻尼 & 主角钉在中心附近
      for (const n of nodes) {
        n.vx += (cx - n.x) * (n.role === 'protagonist' ? 0.012 : 0.006)
        n.vy += (cy - n.y) * (n.role === 'protagonist' ? 0.012 : 0.006)
        n.vx *= 0.82; n.vy *= 0.82
        n.x += Math.max(-6, Math.min(6, n.vx))
        n.y += Math.max(-6, Math.min(6, n.vy))
        n.x = Math.max(n.r, Math.min(size.w - n.r, n.x))
        n.y = Math.max(n.r, Math.min(size.h - n.r, n.y))
      }
      setTick(t)
      if (t < 260) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [size.w, size.h, topChars.length])

  const byName = new Map(nodesRef.current.map((n) => [n.name, n]))
  const [sel, setSel] = useState<string | null>(null)

  return (
    <div className="relative h-[480px] w-full">
      <svg ref={ref} width={size.w} height={size.h}>
        {edges.map((e, i) => {
          const a = byName.get(e.source), b = byName.get(e.target)
          if (!a || !b) return null
          const color = EDGE_COLOR[e.label] || '#b6ab98'
          return (
            <g key={i}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    stroke={color} strokeWidth={Math.min(3, 0.8 + e.weight * 0.25)}
                    opacity={e.label === '交集' ? 0.28 : 0.7} />
              {e.label !== '交集' && (
                <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 3}
                      fontSize={10} fill={color} textAnchor="middle"
                      style={{ fontWeight: 600 }}>
                  {e.label}
                </text>
              )}
            </g>
          )
        })}
        {nodesRef.current.map((n) => {
          const isSel = sel === n.name
          const fill = n.role === 'protagonist' ? '#DC4F3B'
            : n.role === 'supporting' ? '#b45309' : '#8a8070'
          return (
            <g key={n.name} className="cursor-pointer" onClick={() => { setSel(n.name); onSelect?.(n.name) }}>
              {isSel && <circle cx={n.x} cy={n.y} r={n.r + 5} fill="none" stroke="#d97706" strokeWidth={1.5} />}
              <circle cx={n.x} cy={n.y} r={n.r} fill={fill}
                      opacity={n.role === 'minor' ? 0.7 : 0.95} stroke="#fff" strokeWidth={1.5} />
              <text x={n.x} y={n.y + 3.5} fontSize={n.r > 20 ? 12 : 9.5}
                    fill="#fff" textAnchor="middle" style={{ fontWeight: 700, pointerEvents: 'none' }}>
                {n.name.length > 3 ? n.name.slice(0, 3) : n.name}
              </text>
              <text x={n.x} y={n.y + n.r + 13} fontSize={10.5} fill="var(--r-muted, #8a8178)"
                    textAnchor="middle" style={{ pointerEvents: 'none' }}>
                {n.name}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="pointer-events-none absolute bottom-1 left-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-[var(--chrome-muted)]">
        {Object.entries(EDGE_COLOR).slice(0, 7).map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1">
            <i className="inline-block h-0.5 w-3" style={{ background: v }} />{k}
          </span>
        ))}
      </div>
      <span className="hidden">{tick}</span>
    </div>
  )
}
