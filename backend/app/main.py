"""AI 读者阅读系统 —— FastAPI 入口。

启动：uvicorn app.main:app --reload --port 8000
文档：/docs（Swagger） /redoc /openapi.json
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import CORS_ORIGINS, PERSONAS, DENSITY_PROFILES
from .api import books as api_books
from .api import analysis as api_analysis
from .api import annotations as api_annotations
from .api import chat as api_chat
from .api import branches as api_branches
from .api import reader as api_reader
from .api import share as api_share
from .ws import router as ws_router
from .ai.provider import llm_ready

app = FastAPI(
    title="AI 读者阅读系统 API",
    description="AI 陪你看小说，还能帮你改小说 —— 书架 / 多角色批注 / 问答讨论 / 读者分支",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (api_books.router, api_analysis.router, api_annotations.router,
          api_chat.router, api_branches.router, api_reader.router,
          api_share.router, ws_router):
    app.include_router(r)


@app.on_event("startup")
def _autoseed():
    """首次启动且书架为空时，自动装入预置演示书（公有领域文本）。"""
    if os.environ.get("AIREADER_NO_SEED"):
        return
    try:
        if db.query_one("SELECT COUNT(*) c FROM books")["c"] == 0:
            from .seed import run as seed_run
            seed_run()
    except Exception as e:  # noqa: BLE001
        print("[seed] skipped:", e)


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm_ready(), "personas": len(PERSONAS)}


@app.get("/api/personas")
def personas():
    return PERSONAS


@app.get("/api/density-profiles")
def density_profiles():
    return DENSITY_PROFILES


@app.get("/api/settings/reader")
def get_reader_settings():
    return db.setting_get("reader_settings", {})


from pydantic import BaseModel  # noqa: E402


class SettingsBody(BaseModel):
    settings: dict


@app.put("/api/settings/reader")
def put_reader_settings(body: SettingsBody):
    db.setting_set("reader_settings", body.settings)
    return {"ok": True}


# 生产形态：挂载前端构建产物
FRONTEND_DIST = Path(os.environ.get(
    "AIREADER_FRONTEND",
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"))
if FRONTEND_DIST.exists():
    class SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            from starlette.exceptions import HTTPException as Starlette404
            try:
                return await super().get_response(path, scope)
            except Starlette404 as e:
                if e.status_code == 404 and not path.startswith(("api/", "ws")):
                    return FileResponse(FRONTEND_DIST / "index.html")
                raise

    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
