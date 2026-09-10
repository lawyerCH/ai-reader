/** Canvas 海报渲染：金句海报 / AI 观点图 / 笔记长图 / 数据海报 / 分支对比卡 / GIF 帧。 */
import { DEFAULT_COLORS } from '../components/PersonaAvatar'

export interface PosterInput {
  title: string
  author: string
  quote?: string
  persona?: string
  personaName?: string
  opinion?: string
  noteLines?: string[]
  stats?: { label: string; value: string }[]
  original?: string
  rewritten?: string
  branchName?: string
  qr?: HTMLImageElement | null
  palette?: [string, string, string] // deep, accent, paper
}

const PALETTES: Record<string, [string, string, string]> = {
  brown: ['#6b451a', '#d97706', '#f8f1e2'],
  teal: ['#0f5751', '#0f766e', '#e9f4f2'],
  red: ['#8f2c20', '#dc4f3b', '#fbecea'],
  blue: ['#1e3a69', '#2563eb', '#eaf0fb'],
  purple: ['#55268f', '#7c3aed', '#f2ebfc'],
  pink: ['#8f2b63', '#db4a8d', '#fceaf3'],
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const ch of text) {
    if (ch === '\n') { lines.push(line); line = ''; continue }
    if (ctx.measureText(line + ch).width > maxW && line) {
      lines.push(line); line = ch
    } else line += ch
  }
  if (line) lines.push(line)
  return lines
}

function drawQr(ctx: CanvasRenderingContext2D, img: HTMLImageElement | null | undefined,
                x: number, y: number, s: number) {
  if (img) {
    ctx.drawImage(img, x, y, s, s)
  } else {
    ctx.fillStyle = '#fff'
    roundRect(ctx, x, y, s, s, 8); ctx.fill()
    ctx.fillStyle = '#999'; ctx.font = '18px sans-serif'; ctx.textAlign = 'center'
    ctx.fillText('AI 读书会', x + s / 2, y + s / 2)
    ctx.textAlign = 'left'
  }
}

function header(ctx: CanvasRenderingContext2D, W: number, deep: string, accent: string,
                title: string, author: string) {
  ctx.fillStyle = deep
  ctx.textAlign = 'center'
  ctx.font = '700 20px "Noto Sans SC", sans-serif'
  ctx.fillText('AI 读书会 · 陪读手账', W / 2, 54)
  ctx.fillStyle = accent
  ctx.fillRect(W / 2 - 26, 68, 52, 3)
  ctx.textAlign = 'left'
  void title; void author
}

export function drawQuotePoster(canvas: HTMLCanvasElement, input: PosterInput, paletteKey = 'brown') {
  const [deep, accent, paper] = input.palette || PALETTES[paletteKey] || PALETTES.brown
  const W = 750, H = 1100
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = paper; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = deep
  ctx.fillRect(0, 0, W, 14)
  header(ctx, W, deep, accent, input.title, input.author)

  ctx.fillStyle = accent
  ctx.font = '64px Georgia, serif'
  ctx.fillText('“', 88, 190)
  ctx.fillStyle = deep
  ctx.font = '600 40px "Noto Serif SC", "Songti SC", serif'
  const lines = wrap(ctx, input.quote || '', W - 170)
  let y = 260
  for (const l of lines.slice(0, 10)) {
    ctx.fillText(l, 92, y); y += 62
  }
  ctx.fillStyle = accent; ctx.font = '52px Georgia, serif'
  ctx.fillText('”', W - 130, y + 10)

  ctx.strokeStyle = accent; ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(92, H - 250); ctx.lineTo(220, H - 250); ctx.stroke()
  ctx.fillStyle = deep
  ctx.font = '600 30px "Noto Serif SC", serif'
  ctx.fillText(`《${input.title}》`, 92, H - 200)
  ctx.font = '400 22px "Noto Sans SC", sans-serif'
  ctx.fillStyle = '#7a6d59'
  ctx.fillText(input.author ? `${input.author} 著` : '佚名', 92, H - 162)

  drawQr(ctx, input.qr, W - 150, H - 188, 92)
  ctx.fillStyle = '#9a8d78'; ctx.font = '16px sans-serif'; ctx.textAlign = 'center'
  ctx.fillText('扫码加入 AI 读书会', W - 104, H - 80)
  ctx.textAlign = 'left'
}

export function drawOpinionPoster(canvas: HTMLCanvasElement, input: PosterInput) {
  const persona = input.persona || 'plot'
  const deep = DEFAULT_COLORS[persona] || '#b45309'
  const W = 750, H = 1000
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#f7f4ee'; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = deep; ctx.fillRect(0, 0, W, 180)
  ctx.fillStyle = '#fff'; ctx.textAlign = 'center'
  ctx.font = '700 34px "Noto Sans SC", sans-serif'
  ctx.fillText(`AI 读书会 · ${input.personaName || '批注'}`, W / 2, 78)
  ctx.font = '400 20px sans-serif'; ctx.globalAlpha = 0.85
  ctx.fillText(`关于《${input.title}》的一条批注`, W / 2, 120)
  ctx.globalAlpha = 1; ctx.textAlign = 'left'

  roundRect(ctx, 50, 150, W - 100, H - 330, 18)
  ctx.fillStyle = '#fff'; ctx.fill()
  ctx.fillStyle = deep
  ctx.font = '600 27px "Noto Serif SC", serif'
  let y = 210
  for (const l of wrap(ctx, input.opinion || '', W - 140).slice(0, 16)) {
    ctx.fillText(l, 80, y); y += 46
  }
  if (input.quote) {
    y += 10
    ctx.fillStyle = '#8a8070'; ctx.font = 'italic 20px "Noto Serif SC", serif'
    for (const l of wrap(ctx, '原文：' + input.quote, W - 140).slice(0, 4)) {
      ctx.fillText(l, 80, y); y += 34
    }
  }
  drawQr(ctx, input.qr, W / 2 - 55, H - 140, 110)
}

export function drawNotesPoster(canvas: HTMLCanvasElement, input: PosterInput) {
  const [deep, accent, paper] = ['#6b451a', '#d97706', '#fbf6ea']
  const lines = input.noteLines || []
  const H = Math.max(1200, 260 + lines.length * 74)
  const W = 750
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = paper; ctx.fillRect(0, 0, W, H)
  header(ctx, W, deep, accent, input.title, input.author)
  ctx.fillStyle = deep; ctx.textAlign = 'center'
  ctx.font = '700 38px "Noto Serif SC", serif'
  ctx.fillText(`《${input.title}》AI 陪读笔记`, W / 2, 150)
  ctx.textAlign = 'left'
  let y = 215
  ctx.font = '400 23px "Noto Serif SC", serif'
  for (const raw of lines.slice(0, 40)) {
    const persona = raw.match(/^\[(\w+)\]/)?.[1]
    const text = raw.replace(/^\[\w+\]/, '')
    if (persona) {
      ctx.fillStyle = DEFAULT_COLORS[persona] || accent
      roundRect(ctx, 70, y - 22, 8, 8, 4); ctx.fill()
      ctx.fillStyle = deep
    } else {
      ctx.fillStyle = '#4a4033'
    }
    for (const l of wrap(ctx, text, W - 170).slice(0, 4)) {
      ctx.fillText(l, 92, y); y += 38
    }
    y += 18
  }
  drawQr(ctx, input.qr, W - 140, H - 120, 86)
}

export function drawStatsPoster(canvas: HTMLCanvasElement, input: PosterInput) {
  const [deep, accent, paper] = ['#3f3426', '#b45309', '#f6efe0']
  const W = 750, H = 1100
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = paper; ctx.fillRect(0, 0, W, H)
  header(ctx, W, deep, accent, input.title, input.author)
  ctx.fillStyle = deep; ctx.textAlign = 'center'
  ctx.font = '700 40px "Noto Serif SC", serif'
  ctx.fillText('我的阅读年报', W / 2, 160)
  const stats = input.stats || []
  const cols = 2, cw = 280, chh = 200, gx = 40, gy = 230
  stats.slice(0, 8).forEach((s, i) => {
    const x = gx + (i % cols) * (cw + 20)
    const y = gy + Math.floor(i / cols) * (chh + 24)
    roundRect(ctx, x, y, cw, chh, 16)
    ctx.fillStyle = '#fffdf7'; ctx.fill()
    ctx.strokeStyle = '#e3d6bb'; ctx.stroke()
    ctx.fillStyle = accent; ctx.font = '700 52px "Noto Sans SC", sans-serif'
    ctx.fillText(s.value, x + cw / 2, y + 96)
    ctx.fillStyle = '#7a6d59'; ctx.font = '400 22px sans-serif'
    ctx.fillText(s.label, x + cw / 2, y + 146)
  })
  ctx.fillStyle = '#9a8d78'; ctx.font = '20px serif'
  ctx.fillText('AI 读书会 · 让每本书都有人陪你讨论', W / 2, H - 90)
  drawQr(ctx, input.qr, W / 2 - 55, H - 80 + 0, 0)
  ctx.textAlign = 'left'
}

/** 分支对比卡（单张） */
export function drawCompareFrame(canvas: HTMLCanvasElement, input: PosterInput, showRewrite: boolean) {
  const W = 750, H = 1000
  canvas.width = W; canvas.height = H
  const ctx = canvas.getContext('2d')!
  const bg = showRewrite ? '#eaf5ef' : '#f3eee5'
  const deep = showRewrite ? '#15803d' : '#57504a'
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = deep; ctx.fillRect(0, 0, W, 120)
  ctx.fillStyle = '#fff'; ctx.font = '700 30px "Noto Sans SC", sans-serif'; ctx.textAlign = 'center'
  ctx.fillText(showRewrite ? `读者分支：${input.branchName || '我的改写'}` : '原版情节', W / 2, 72)
  ctx.textAlign = 'left'
  roundRect(ctx, 44, 150, W - 88, H - 230, 16)
  ctx.fillStyle = '#fff'; ctx.fill()
  ctx.fillStyle = '#2b2620'
  ctx.font = '400 25px "Noto Serif SC", serif'
  let y = 200
  const text = (showRewrite ? input.rewritten : input.original) || ''
  for (const l of wrap(ctx, text, W - 132).slice(0, 22)) {
    ctx.fillText(l, 66, y); y += 44
  }
  ctx.fillStyle = deep; ctx.font = '18px sans-serif'; ctx.textAlign = 'center'
  ctx.fillText(showRewrite ? '● 改写版' : '○ 原版', W / 2, H - 56)
  ctx.textAlign = 'left'
}

export function downloadCanvas(canvas: HTMLCanvasElement, filename: string) {
  const a = document.createElement('a')
  a.download = filename
  a.href = canvas.toDataURL('image/png')
  a.click()
}
