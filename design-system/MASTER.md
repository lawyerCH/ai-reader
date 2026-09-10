# AI 读书会 · 设计系统主文件（Design Master）

依据 ui-pro-max skill 的设计流程产出（design-system/ai-reader），落地于
`frontend/tailwind.config.js` 与 `frontend/src/index.css`。

## 1. 设计模式（Pattern）

- 风格：Minimalism（极简主义）+ 书籍装帧感（editorial）
- 对标：微信读书 / 起点读书；用色走「牛皮纸 + 书棕 + 琥珀金」暖色书系，
  避免工具化蓝紫配色。
- 情绪关键词：安静、纸感、陪伴、讨论。
- 布局：桌面端为「目录 / 正文 / AI 面板」三栏；移动端为单栏 + 底部抽屉；
  4 / 8 px 间距节奏，卡片圆角 14px，正文行长 38em（65–70 中文字/行）。
- 动效：`riseIn 340ms cubic-bezier(.22,1,.36,1)`、`popIn 200ms`，
  遵守 `prefers-reduced-motion`；无超过 2 个并发动画。

## 2. 色彩（Colors）

App 框架色（来自 skill 输出的 Book & Reading Tracker 暖色系）：

| token | 值 | 用途 |
| --- | --- | --- |
| `--brand` | `#8a5a24` | 品牌主色（书棕） |
| `--brand-deep` | `#6b451a` | hover/深色态 |
| `--brand-soft` | `#d97706` | 进度条/强调（琥珀） |
| `--chrome-bg` | `#f5efe3` | 页面底色（米灰） |
| `--chrome-panel` | `#fffcf6` | 卡片/面板 |
| `--chrome-ink` | `#2b2620` | 正文 |
| `--chrome-muted` | `#83796c` | 次要文字 |
| `--chrome-border` | `#e7ddcb` | 描边 |

六个 AI 角色的识别色（同时用于批注卡片、关系边、头像）：

| 角色 | 色值 | 语义 |
| --- | --- | --- |
| 剧情党 | `#DC4F3B` | 情节/伏笔（朱红） |
| 考据党 | `#2563EB` | 设定/历史（靛蓝） |
| 情感分析师 | `#DB4A8D` | 情绪/关系（玫粉） |
| 吐槽君 | `#B45309` | 套路/逻辑（赭石） |
| 文学教授 | `#0F766E` | 修辞/叙事（松绿） |
| 角色本人 | `#7C3AED` | 第一人称代入（紫） |

阅读主题（10 套，`data-theme` 切换）：米白、雪白、羊皮纸、护眼绿、淡蓝、
樱花粉、灰墨、夜间棕、深夜灰、纯黑 AMOLED；每套含 `--r-bg/--r-fg/--r-card/
--r-border/--r-accent` 5 个变量，深浅模式覆盖白天与夜间场景。

## 3. 排版（Typography）

- 界面字体：Noto Sans SC（回退 system-ui / PingFang / 雅黑）。
- 正文 6 选 1：思源宋体、经典宋体、思源黑体、楷体、明朝体、圆体。
- 字号 15–30px 无级滑块；行高 1.4–2.6；段距 0.4–2.6em；字距 0–0.12em。
- 标题用 Noto Serif SC 700，字距 0.12em；西文点缀 Cormorant Garamond。
- 高亮五色：黄/绿/蓝/粉/橙，半透明 `rgba(..., .26-.32)`。

## 4. 效果（Effects）

- 卡片阴影 `0 1px 2px rgba(60,45,20,.06), 0 10px 28px rgba(60,45,20,.08)`。
- 弹层：桌面居中 pop，移动端 bottom sheet（圆角仅顶部），遮罩 45% 黑。
- 正文批注：段落后以 20px 圆点角标悬浮，hover 放大 1.18；
  面板卡片左侧/头像用角色色，不使用 emoji 作为结构性图标。
- 图标统一使用 @phosphor-icons/react（duotone/regular 字重）。

## 5. 无障碍（Accessibility）

- 正文对比度 ≥ 4.5:1；夜间三主题覆盖暗光。
- 触控目标 ≥ 38px（`.icon-btn` / `.btn`），底部栏 48px 并留安全区。
- 所有按钮含 `title` / `aria-label`；图标按钮无文字时提供描述。
- 五断点：<768 手机单栏 / 768–1023 平板抽屉 / 1024–1279 / 1280–1535 / ≥1536。
