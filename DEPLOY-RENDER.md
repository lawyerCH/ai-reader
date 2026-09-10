# 部署到 Render 指南

本项目是 **AI 读者阅读系统** 的部署副本（`render-deploy/`），与开发原项目完全隔离。
部署采用 **两个服务** 的架构，后端保持纯 Python，前端走 Render 免费 CDN。

## 架构

```
用户浏览器
   │
   ├─ https://ai-reader-web.onrender.com   （Static Site，CDN，免费，不休眠）
   │     └─ Vite 构建产物（React SPA + PWA）
   │           └─ VITE_API_BASE=https://ai-reader-api.onrender.com
   │
   └─ https://ai-reader-api.onrender.com   （Python Web Service）
         ├─ FastAPI：/api/*（REST）
         ├─ WebSocket：/ws/*（问答流式）
         └─ SQLite（backend/data/ai_reader.db，免费套餐为临时文件系统）
```

- 前端 `api.ts` 已支持 `VITE_API_BASE` 环境变量；**未设置时回落同源**，本地开发行为不变。
- 后端 CORS 为 `CORS_ORIGINS + ["*"]`（全开），跨域开箱即通；`config.py` 新增
  `AIREADER_CORS_ORIGINS` 环境变量可追加白名单（纯增量，不改默认行为）。

## 前置条件

1. **代码必须在 Git 仓库中**（Render 无法从本地目录部署）。
   - 需要 GitHub / GitLab / Bitbucket 账号，把本目录推上去。
   - 本地仓库**已初始化**（分支 `main`，含首次提交），只差推送到远端。
2. Render 账号（免费注册即可）。

## 部署步骤

```bash
# 1. 推送到远端（本地仓库已初始化，在 render-deploy/ 目录内）
cd render-deploy
# 先在 GitHub 网页上新建一个空仓库（不要勾选 README/.gitignore），然后：
git remote add origin https://github.com/<你的账号>/ai-reader.git
git push -u origin main
```

> 注意 `.gitignore` 已排除 `node_modules/`、`.venv/`、`dist/`、`backend/data/` 等，
> 提交前可用 `git status` 确认没有大文件混入。

2. 打开 Render Dashboard → **New → Blueprint** → 连接刚才的仓库。
3. 确认 `render.yaml` 被识别（两个服务：`ai-reader-api` + `ai-reader-web`），点 **Deploy Blueprint**。
4. 等两个服务都显示 **Live**，打开 `https://ai-reader-web.onrender.com` 即可使用。

## 免费套餐的取舍（重要）

| 项目 | 免费 | 付费（Starter，$7/月） |
|---|---|---|
| 后端实例 | 0.1 CPU / 512MB | 0.5 CPU / 512MB |
| 休眠 | 15 分钟无流量即休眠，唤醒约 1 分钟 | 可关闭休眠 |
| 数据持久 | ❌ 重启/重部署/休眠后 SQLite 与上传书籍丢失 | ✅ 挂持久盘（`disk` 配置已备好） |
| 实例小时 | 750 小时/月（单服务常驻刚好够） | 按套餐 |
| 前端静态站 | ✅ 免费、CDN、不休眠 | 免费 |

**结论**：免费套餐适合体验/演示；要长期稳定使用（用户上传的书不丢、不冷启动），
建议升级付费并取消 `render.yaml` 中 `disk` 段的注释（数据目录 `AIREADER_DATA=/var/data`）。

## 可选配置

### 接入真实大模型（不配置也能用）

系统内置本地启发式引擎，零配置即可完整运行。要接入 OpenAI 兼容大模型：

1. 在 Render Dashboard 的 `ai-reader-api` → Environment 添加：
   - `AIREADER_LLM_BASE_URL`（如 `https://api.openai.com/v1`）
   - `AIREADER_LLM_API_KEY`
   - `AIREADER_LLM_MODEL`（默认 `gpt-4o-mini`）
2. 保存并重新部署。`/api/health` 的 `llm` 字段会变为 `true`。

### 关闭自动装书

首次启动且书架为空时，后端会自动装入 3 本鲁迅演示书（公有领域）。
若不需要，给 `ai-reader-api` 设置环境变量 `AIREADER_NO_SEED=1`。

## 国内访问说明

- Render 无大陆节点，最近为新加坡（RTT 约 60-100ms）；`onrender.com` 未被封锁但不保证稳定。
- 免费套餐 1 分钟冷启动对国内用户是"打不开"的体验，建议至少升级付费关闭休眠。
- 若面向国内正式分发，更优方案是香港/新加坡轻量 VPS（无需备案）或国内云+备案。

## 本地验证（可选，部署前自查）

```bash
# 后端（在 render-deploy/backend）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001
# 另开终端：
curl http://127.0.0.1:8001/api/health   # {"ok":true,...}

# 前端（在 render-deploy/frontend）
npm ci
VITE_API_BASE=http://127.0.0.1:8001 npm run build   # 模拟跨域构建
npm run preview -- --port 4173
# 打开 http://localhost:4173 验证
```

## 本地已验证的行为

以下均在本地按 Render 的构建/启动命令逐项实测通过（2025-09 验证）：

| 项目 | 结果 |
| --- | --- |
| 后端冷启动（`data/` 不存在） | 自动创建目录 + 自动装书 3 本鲁迅（269 条批注） |
| `GET /api/health` | 200，无 LLM Key 时 `llm:false`，走本地启发式引擎 |
| `GET /api/books` 跨域 | 200，CORS 预检与实际请求均通过 |
| `WebSocket /ws/read/{bid}` 跨域 | 连接成功，收到 `annotation`/`digest`/`done` 事件 |
| 前端构建（设 `VITE_API_BASE`） | 值内联进产物；未设时为 0 处引用，回落同源 |
| `wsUrl()` scheme 推导 | 裸主机名 / `https` / `http` 三种形态均正确映射到 `ws(s)://` |
| API-only 模式（无 `frontend/dist`） | `/` 404、`/api/*` 200、`/docs` 200（符合设计） |
| 后端测试 `pytest tests/test_api.py` | 8 passed |
| 前端测试 `npm test` | 5 passed |

## 已知问题（沿袭原项目，未修改）

这些行为与原项目完全一致，本次部署副本**刻意不改**，以保持两边一致：

1. **阅读时长不记录**：前端 `Reader.tsx` 创建阅读会话时使用了章节详情接口不存在的
   `word_count` 字段，导致 `POST /api/books/{id}/sessions` 恒返回 422，
   且前端静默忽略该错误 —— 功能上不影响阅读，只是"阅读时长统计"永远为空。
2. **`tests/test_nlp.py` 无法收集**：`tests/` 目录缺 `__init__.py`，相对导入失败。
   `pytest tests/test_api.py` 可正常运行，`render.yaml` 的 `healthCheckPath` 也不依赖测试。

## 常见问题

- **页面能开但接口报错**：检查 `ai-reader-api` 是否已 Live；免费套餐冷启动期间请求会失败。
- **上传的书重启后消失**：免费套餐无持久盘，属预期；升级付费并挂盘。
- **WebSocket 连不上**：确认浏览器访问的是 `https`（`wsUrl` 会自动用 `wss`）。
- **改了前端不生效**：确认推到了 Blueprint 链接的分支，且 `ai-reader-web` 重新构建成功。