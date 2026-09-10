# AI 读书会 · 陪读阅读器

> **AI 陪你看小说，还能帮你改小说。**
> 导入小说即自动生成人物图谱、伏笔回收与六角色 AI 批注；边读边与「剧情党 / 考据党 /
> 情感分析师 / 吐槽君 / 文学教授 / 角色本人」讨论；选中段落用一句话改结局，
> 分支成树、随时切回原版。

本项目为全栈实现，包含三端运行形态：

- **Web（PWA，可离线）**：React + TypeScript + Vite，移动端 H5 / 桌面端自适应；
- **后端服务**：Python FastAPI，RESTful + 3 条 WebSocket；
- **桌面端（Tauri 思路的 Electron 实现）**：原生窗口，自动拉起本地后端。

> 演示书：《阿Q正传》《孔乙己》《一件小事》（鲁迅，公有领域），首次启动自动入库，
> 开箱即有约 **270 条六角色批注、33 个人物节点、7 个地点、2 个示例读者分支**。

---

## 一、快速开始

### 0. 环境
- Python 3.10+；Node 18+（构建前端 / 桌面端需要）。

### 1. 后端

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
# 首次启动若书架为空，会自动 seed 三本公有领域演示书（约 2 秒/本分析）
# 交互式 API 文档：http://127.0.0.1:8000/docs （47 个接口，含 WebSocket）
```

### 2. 前端（开发模式，热更新）

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173 ，已把 /api、/ws 代理到 8000
```

生产构建（后端会自动托管 `frontend/dist`，只跑一个端口）：

```bash
cd frontend && npm run build
# 访问 http://127.0.0.1:8000 即为完整应用
```

### 3. 桌面端（Electron）

```bash
cd desktop
npm install
npm start
# 默认在本机 spawn 后端（python3 -m uvicorn）；
# 也可 AIREADER_SERVER=http://x:8000 npm start 连接远程/已启动的服务
```

### 4. PWA / 移动端 H5
- 浏览器打开网页端后「添加到主屏幕」即得到近原生 App：离线壳 + API NetworkFirst 缓存；
- H5 形态已做：390px/430px 布局、安全区、底部工具栏、点按选段、底部抽屉面板、
  触控目标 ≥38px。

---

## 二、核心功能对照

### 模块一：书架与导入
- TXT / Markdown / EPUB / PDF 四格式解析；批量多文件上传、拖拽、粘贴文本（`POST /api/books/import`、`/import/text`）。
- 自动识别书名、作者、章/节/卷/回/Markdown 标题，硬换行重组段落，封面用确定性 SVG 装帧自动生成。
- 书架按「在读/已读/搁置/想读」筛选、排序、搜索；元信息可编辑、可删除；阅读进度跨端保存。

### 模块二：六角色 AI 多角色批注（重点）
| 角色 | 职责 | 典型批注信号 |
| --- | --- | --- |
| 剧情党 | 伏笔埋设/回收、转折、章末钩子、预测 | `foreshadow_plant/payoff`、`turning_point`、`cliffhanger`、`prediction` |
| 考据党 | 世界观设定、新地点/组织/功法、历史名词、前后一致性 | `new_location`、`new_setting`、`title_gloss`（含 28 条清末历史词条） |
| 情感分析师 | 双人情绪同框、恋爱节点、密集对白、潜台词 | `relationship_moment`、`romance`、`subtext` |
| 吐槽君 | 网文套路（坠崖奇遇/系统流/邪魅一笑等 22 条）、逻辑巧合、名场面 | `trope`、`logic_smell`、`signature_scene` |
| 文学教授 | 比喻、反复、反讽、元叙事、插叙/补叙、环境定调 | `simile`、`repetition`、`irony`、`meta_narrative`、`flashback` |
| 角色本人 | 以人物第一人称在其关键段落开口（阿Q/赵太爷/吴妈等定制声口） | `in_character` |

- 批注锚定到**章节×段落**，正文显示角色圆点角标，不遮挡阅读；
- 四档密度：密集 / 适中 / 稀疏 / 仅关键；每个角色可单独开关；
- 每章有**章末小结**：中性抽取摘要 + 金句 + 各角色精华；
- 打开章节时 WebSocket `/ws/read/{book}` 会「逐条弹出」批注，模拟真人边读边评。

### 模块三：AI 陪读实时分析
- **人物档案**：中文人名识别（姓氏边界扫描 + 称谓模式 + 对白归属 + 跨章频次），
  含主角/配角/群演分级、性格词、情绪统计、代表台词、自然语言小传。
- **关系图谱**：冲突/亲缘/爱慕/师徒/朋友五类边，力导向 SVG 图（可点节点看档案）。
- **时间线**：抽取「时间锚点 + 动作词」事件，每章 1–3 条，可点击跳章。
- **地点地图**：后缀感知扫描（祠/庵/寺/镇/城/崖/洞…），放射式空间图 + 语境释义。
- **设定百科**：组织/地点/功法/文献作品四类可检索词条。
- **前情提要**：带进度重开自动生成：前文分章梗概 + 近期活跃人物 + 未回收伏笔。

### 模块四：问答与讨论
- 全书 / 当前章问答：BM25 中文 bigram 检索 + 意图识别（结局/人物/关系/地点/解释/预测…）+ 引用原文；
- **读书会**：一个问题五个角色各自表态；
- **角色辩论**：剧情党 vs 吐槽君自动多轮立论—反驳（回合制）；
- **脑洞讨论（What-if）**：每个角色对「如果……」给出因果链脑补；
- REST `POST /ask /discuss /debate /whatif`；WebSocket `/ws/chat/{book}` 流式打字机。

### 模块五：读者分支（重点）
- 划选段落即出现工具条：5 色高亮、问 AI、**改写**、金句海报、书签；
- 一句话指令（「让主角活下来沉冤得雪」「把这个人写成幕后反派」「CP 在一起」「悲剧收场」）；
- 范围：段落 / 章节 / 结局 / 全篇；意图与目标人物自动解析，改写保证实体一致；
- WebSocket `/ws/rewrite/{book}` 逐句流式生成，自动存为分支；
- **分支树**：原版为根，分支可继续分叉，删除后子分支自动挂回；
- 阅读时一键切换版本，被改段落有琥珀色标记；支持分支级 **TXT / Markdown / EPUB 导出**。
- 未配置大模型时由内置的实体感知模板引擎完成（零依赖可用）；配置 OpenAI 兼容接口后自动切换真实 LLM。

### 模块六：阅读器体验
- 10 套背景主题（米白/雪白/羊皮纸/护眼绿/淡蓝/樱花粉/灰墨/夜间棕/深夜灰/纯黑）；
- 6 种正文字体，字号、行间距、段间距、字间距无级调节（滑块 15–30px 等）；
- **连续滚动**（到底自动续章）与**仿真翻页**（CSS multicol 分页 + 点按/滑动翻页）双模式；
- 顶部阅读进度条、章末「上一章/下一章」、侧滑目录、书签与高亮云端持久化。

### 模块七：数据看板
- 日阅读时长面积图、总字数/时长/活跃日/读完数；
- 六角色互动条数（彩色条形图）、分支创建数与改写字数、每本书笔记/报告导出入口。

### 模块八：分享中心（选中→生成，最多两步）
- **金句海报**（书棕装帧 + 二维码）、**AI 观点图**（角色配色）、**笔记长图**
  （章末小结+批注）、**数据海报**（年报卡片）；
- **读者分支分享卡 + 原版⇄改写 GIF**（前端 gifenc 编码，三帧循环）；
- 二维码由后端 `GET /api/qrcode` 实时生成。

### 导出 / 离线
- 全书、读者分支：TXT / Markdown / EPUB；AI 陪读笔记 Markdown、阅读报告 Markdown；
- PWA 预缓存应用壳；小说全文与分析结果存本地 SQLite，断网可读。

---

## 三、系统架构

```
┌──────────────────────────┐      ┌───────────────────────────────┐
│  Web / H5 / PWA (5173)   │      │  Electron 桌面（自动 spawn 后端）│
│  React18 + TS + Tailwind │      └───────────────┬───────────────┘
│  zustand / recharts /    │◄── REST / WS ───────►│
│  canvas 海报 / GIF       │                       ▼
└──────────────────────────┘        ┌───────────────────────────────┐
                                    │ FastAPI (app.main, :8000)      │
                                    │  books / analysis / annotations│
                                    │  chat / branches / reader/share│
                                    │  ws: read 陪读 / rewrite / chat│
                                    └───────┬───────────────┬───────┘
                                            │               │
                          SQLite (data/)    │               ▼
        书籍/章节/批注/人物/分支/进度/高亮    ▼        ai/ 本地启发式引擎
        (首次启动 seed 公有领域演示书)   parser/        ─ nlp：人名/对白/共现
                                         epub/pdf       ─ analyze：关系/时间线/地点/伏笔
                                                        ─ annotations：六角色规则引擎
                                                        ─ qa：BM25 + 意图 + 多角色
                                                        ─ rewrite：意图解析 + 多幕生成
                                                        ─ provider：可选 OpenAI 兼容 LLM
```

- **零模型默认路径**：所有 AI 功能（227+ 条批注、问答、辩论、结局改写）均由确定性的
  中文 NLP 规则引擎产出，导入即得、离线可用；
- **可选 LLM 升级**：配置环境变量即可把问答/改写切到真实大模型（流式）：

```bash
export AIREADER_LLM_BASE_URL="https://api.openai.com/v1"
export AIREADER_LLM_API_KEY="sk-..."
export AIREADER_LLM_MODEL="gpt-4o-mini"   # 任意 OpenAI Chat Completions 兼容服务
```

## 四、主要 API（完整 47 个见 /docs 与 docs/openapi.json）

| 类别 | 接口 |
| --- | --- |
| 书架 | `GET/POST /api/books`，`PATCH/DELETE /api/books/{id}`，`GET /cover`、`GET /chapters[/{idx}]` |
| 批注 | `GET /annotations?chapter&personas&density`、`GET /chapters/{idx}/digest`、`GET /personas` |
| 分析 | `GET /characters[/{name}]`、`/relations`、`/timeline`、`/locations`、`/settings`、`/foreshadows`、`/recap` |
| 讨论 | `POST /ask`、`/discuss`、`/debate`、`/whatif`、会话持久化 `/conversations` |
| 分支 | `POST /branches`、`GET /branches/tree`、`/branches/{id}/materialized`、`/branches/{id}/export` |
| 阅读 | `PUT /progress`、书签/高亮增删、`POST /sessions`、`GET /stats/overview` |
| 分享 | `GET /qrcode?data=`、`GET /export?type=notes|report&format=txt|md|epub` |
| WebSocket | `/ws/read/{id}` 陪读流、`/ws/rewrite/{id}` 流式改写、`/ws/chat/{id}` 流式问答 |

## 五、测试与质量

```bash
cd backend && python -m pytest                                  # 16 个用例
python -m pytest --cov=app --cov-report=term --cov-report=html:docs/htmlcov
cd frontend && npx vitest run                                   # 前端 5 个用例
```

- 后端 16 项覆盖：四格式解析、人物/关系/地点抽取、六角色批注生成、
  问答/多角色/辩论/脑洞、分支创建/树/导出、进度/书签/高亮/统计、二维码、
  EP/PUB 导入与损坏 PDF 降级、两条 WebSocket；**覆盖率 76%**（报告 `backend/docs/htmlcov/index.html`）。
- 前端覆盖格式化与批注密度采样工具。
- 设计依据见 `design-system/MASTER.md`（ui-pro-max skill 产出）。

## 六、目录

```
backend/   FastAPI 服务、AI 引擎、解析器、演示种子（seed/ 公有领域文本）
frontend/  React 阅读器、分享画布、PWA 清单
desktop/   Electron 主进程
design-system/  设计令牌与规范
docs/      OpenAPI 快照、覆盖率报告（运行测试后生成）
```

## 七、版权说明
- 演示文本取自鲁迅小说集，作者逝世已逾 50 年，属公有领域；
- 用户导入的小说仅保存在本地后端数据目录（`backend/data/`），不上传任何第三方。
