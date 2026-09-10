"""全局配置。所有路径默认基于后端目录，可用环境变量覆盖。"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AIREADER_DATA", BACKEND_DIR / "data"))
BOOK_FILES = DATA_DIR / "books"
DB_PATH = DATA_DIR / "ai_reader.db"
COVER_DIR = DATA_DIR / "covers"

for _d in (DATA_DIR, BOOK_FILES, COVER_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# 可选：外接 OpenAI 兼容 LLM（不配置时使用内置本地启发式引擎，功能完整、零依赖可用）
LLM_BASE_URL = os.environ.get("AIREADER_LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.environ.get("AIREADER_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("AIREADER_LLM_MODEL", "gpt-4o-mini")

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "app://.",  # Electron
    "tauri://localhost",
    "http://tauri.localhost",
]

# 追加允许的跨域来源（逗号分隔），用于前后端分离部署
CORS_ORIGINS = _DEFAULT_CORS_ORIGINS + [
    o.strip() for o in os.environ.get("AIREADER_CORS_ORIGINS", "").split(",") if o.strip()
]

# 六个内置 AI 陪读角色（可在前端开关、可扩展）
PERSONAS = [
    {
        "id": "plot",
        "name": "剧情党",
        "emoji_key": "plot",
        "color": "#DC4F3B",
        "accent_bg": "#FDEDEB",
        "tagline": "熟读套路三千本，伏笔没有一处能逃得过我的眼睛。",
        "style": "分析剧情走向、伏笔埋设与回收、猜测后续发展",
    },
    {
        "id": "lore",
        "name": "考据党",
        "emoji_key": "lore",
        "color": "#2563EB",
        "accent_bg": "#E9F0FE",
        "tagline": "设定即法律，世界观的每一砖一瓦我都要核对。",
        "style": "补充世界观背景、设定考据、前后一致性核查",
    },
    {
        "id": "emotion",
        "name": "情感分析师",
        "emoji_key": "emotion",
        "color": "#DB4A8D",
        "accent_bg": "#FCEAF3",
        "tagline": "我关心的不是发生了什么，而是谁的心先动了。",
        "style": "分析人物情感动机、关系变化与潜台词",
    },
    {
        "id": "snark",
        "name": "吐槽君",
        "emoji_key": "snark",
        "color": "#B45309",
        "accent_bg": "#FBF0DD",
        "tagline": "这个桥段？我去年就看过八百遍了。",
        "style": "幽默毒舌，专治逻辑硬伤与套路化情节",
    },
    {
        "id": "professor",
        "name": "文学教授",
        "emoji_key": "professor",
        "color": "#0F766E",
        "accent_bg": "#E6F4F2",
        "tagline": "别急着翻页，我们来聊聊这段叙事的妙处。",
        "style": "写作手法、修辞、叙事结构与文体赏析",
    },
    {
        "id": "character",
        "name": "角色本人",
        "emoji_key": "character",
        "color": "#7C3AED",
        "accent_bg": "#F1EBFE",
        "tagline": "你以为你懂我？来，我亲口告诉你。",
        "style": "以书中人物的第一人称口吻与读者对话",
    },
]
PERSONA_MAP = {p["id"]: p for p in PERSONAS}

# 批注密度档位 -> 最大采样概率 / 每章上限
DENSITY_PROFILES = {
    "dense": {"label": "密集", "per_chapter": 99, "keep": 1.0},
    "normal": {"label": "适中", "per_chapter": 12, "keep": 0.8},
    "sparse": {"label": "稀疏", "per_chapter": 6, "keep": 0.45},
    "keyonly": {"label": "仅关键节点", "per_chapter": 3, "keep": 0.2},
}
