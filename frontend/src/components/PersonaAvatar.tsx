import {
  Detective, Scroll, Heart, SmileyWink, GraduationCap, UserCircle,
  type Icon,
} from '@phosphor-icons/react'

export const PERSONA_ICONS: Record<string, Icon> = {
  plot: Detective,
  lore: Scroll,
  emotion: Heart,
  snark: SmileyWink,
  professor: GraduationCap,
  character: UserCircle,
}

export const PERSONA_LABEL: Record<string, string> = {
  plot: '剧情党',
  lore: '考据党',
  emotion: '情感分析师',
  snark: '吐槽君',
  professor: '文学教授',
  character: '角色本人',
}

export function PersonaAvatar({
  persona, color, size = 28, ring = false,
}: { persona: string; color?: string; size?: number; ring?: boolean }) {
  const Icon = PERSONA_ICONS[persona] || UserCircle
  const c = color || DEFAULT_COLORS[persona] || '#78716c'
  return (
    <span
      title={PERSONA_LABEL[persona]}
      style={{
        background: c, width: size, height: size,
        boxShadow: ring ? `0 0 0 3px ${c}33` : undefined,
      }}
      className="inline-flex shrink-0 items-center justify-center rounded-full text-white">
      <Icon size={Math.round(size * 0.58)} weight="duotone" />
    </span>
  )
}

export const DEFAULT_COLORS: Record<string, string> = {
  plot: '#DC4F3B',
  lore: '#2563EB',
  emotion: '#DB4A8D',
  snark: '#B45309',
  professor: '#0F766E',
  character: '#7C3AED',
}

export const DEFAULT_BG: Record<string, string> = {
  plot: '#FDEDEB',
  lore: '#E9F0FE',
  emotion: '#FCEAF3',
  snark: '#FBF0DD',
  professor: '#E6F4F2',
  character: '#F1EBFE',
}
