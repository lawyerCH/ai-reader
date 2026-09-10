"""确定性 SVG 封面生成：不依赖图片资源，按书名取色，仿实体书装帧。"""
import hashlib

PALETTES = [
    ("#8C5A2B", "#E8C9A0", "#F6EAD8"),  # 牛皮纸
    ("#214E34", "#A8C9A0", "#EDF4E8"),  # 墨绿
    ("#7A2E2E", "#D9A08C", "#F7E8E2"),  # 绛红
    ("#1F3A5F", "#9CB4D2", "#E8EEF6"),  # 黛蓝
    ("#5B3A75", "#C2A8D8", "#F1EAF7"),  # 紫檀
    ("#6E4A1E", "#D8B878", "#F6ECD6"),  # 鎏金
    ("#2F4858", "#93B0BC", "#E6EEF0"),  # 青灰
    ("#5A2A44", "#D09AB4", "#F6E7EF"),  # 藕荷
]


def _palette(seed: str):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return PALETTES[h % len(PALETTES)], h


def make_cover_svg(title: str, author: str = "", intro: str = "") -> str:
    (deep, accent, paper), h = _palette(title + author)
    # 书名竖排/横排自适应
    t = title.strip()
    lines: list[str] = []
    line = ""
    for ch in t:
        line += ch
        if len(line) >= 6:
            lines.append(line)
            line = ""
    if line:
        lines.append(line)
    lines = lines[:3]
    if author:
        author_text = author.strip()[:12]
    else:
        author_text = "佚名"
    author_ys = 300
    title_y0 = 110
    def title_line(y, s):
        return (f'<text x="150" y="{y}" text-anchor="middle" '
                f'font-family="Noto Serif SC, Songti SC, SimSun, serif" '
                f'font-size="34" font-weight="700" fill="{paper}" '
                f'letter-spacing="4">{s}</text>')
    title_svg = "\n  ".join(
        title_line(title_y0 + i * 44, s) for i, s in enumerate(lines))
    deco_y = title_y0 + len(lines) * 44 + 8
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="420" viewBox="0 0 300 420">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{deep}"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0.55"/>
    </linearGradient>
  </defs>
  <rect width="300" height="420" rx="10" fill="url(#g)"/>
  <rect x="16" y="16" width="268" height="388" rx="4" fill="none" stroke="{paper}" stroke-opacity="0.5" stroke-width="1.2"/>
  <rect x="26" y="26" width="248" height="368" rx="2" fill="none" stroke="{paper}" stroke-opacity="0.25"/>
  {title_svg}
  <line x1="100" y1="{deco_y}" x2="200" y2="{deco_y}" stroke="{accent}" stroke-width="1.4"/>
  <circle cx="150" cy="{deco_y}" r="3.2" fill="{accent}"/>
  <text x="150" y="{author_ys + 12}" text-anchor="middle"
        font-family="Noto Serif SC, Songti SC, SimSun, serif" font-size="17" fill="{paper}" opacity="0.92">{author_text} 著</text>
  <text x="150" y="392" text-anchor="middle" font-family="Noto Sans SC, sans-serif"
        font-size="11" fill="{paper}" opacity="0.65" letter-spacing="3">AI READER · 读书会藏书</text>
</svg>"""
