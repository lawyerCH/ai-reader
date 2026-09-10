"""WebSocket：实时陪读批注流、流式改写、流式对话。"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import db
from .db import now
from .ai.loader import load_parsed_book, get_structure
from .ai import rewrite as rw
from .ai import qa
from .config import DENSITY_PROFILES

router = APIRouter()


async def ws_send(ws: WebSocket, event: str, data: dict | None = None, **kw):
    await ws.send_text(json.dumps({"event": event, **(data or {}), **kw}, ensure_ascii=False))


@router.websocket("/ws/read/{bid}")
async def read_along(ws: WebSocket, bid: int):
    """打开章节 -> AI 逐条'弹'批注（模拟真人边读边评），最后给章末小结。"""
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            chapter = msg.get("chapter", 0)
            density = msg.get("density", "normal")
            personas = set(msg.get("personas") or [])
            anns = [dict(r) for r in db.query(
                "SELECT * FROM annotations WHERE book_id=? AND chapter_idx=? "
                "ORDER BY para_idx, priority DESC", (bid, chapter))]
            if personas:
                anns = [a for a in anns if a["persona"] in personas]
            cap = {"dense": 99, "normal": 6, "sparse": 3, "keyonly": 2}[density]
            sent, seen_para = 0, set()
            for a in anns:
                if sent >= cap:
                    break
                # 同一段保留高优
                if a["para_idx"] in seen_para and density in ("sparse", "keyonly"):
                    continue
                seen_para.add(a["para_idx"])
                await ws_send(ws, "annotation", {"annotation": a})
                sent += 1
                await asyncio.sleep(0.35 if density != "dense" else 0.12)
            digest = db.query_one(
                "SELECT summary,highlights FROM chapter_summaries WHERE book_id=? AND chapter_idx=?",
                (bid, chapter))
            if digest:
                await ws_send(ws, "digest", {
                    "summary": digest["summary"],
                    "golden": db.jloads(digest["highlights"], {}).get("golden", [])})
            await ws_send(ws, "done", {"count": sent})
    except WebSocketDisconnect:
        return


@router.websocket("/ws/rewrite/{bid}")
async def stream_rewrite(ws: WebSocket, bid: int):
    await ws.accept()
    try:
        msg = await ws.receive_json()
        book = load_parsed_book(bid)
        st = get_structure(bid)
        scope = msg.get("scope", "paragraph")
        original = msg.get("original_text", "")
        if scope == "paragraph" and not original:
            ch = db.query_one(
                "SELECT paragraphs FROM chapters WHERE book_id=? AND idx=?",
                (bid, msg.get("chapter_idx", 0)))
            paras = db.jloads(ch["paragraphs"], []) if ch else []
            pi = msg.get("para_idx", 0) or 0
            if 0 <= pi < len(paras):
                original = paras[pi]
        plan = rw.parse_instruction(msg.get("instruction", ""), st)
        await ws_send(ws, "plan", {"plan": plan})
        pieces, full = [], ""
        for ev in rw.stream_rewrite(scope, msg.get("instruction", ""), st,
                                   original, msg.get("chapter_idx", 0)):
            if "delta" in ev:
                full += ev["delta"]
                pieces.append(ev["delta"])
                await ws_send(ws, "delta", {"delta": ev["delta"]})
                await asyncio.sleep(0.12)
            elif ev.get("done"):
                meta = ev.get("meta", {})
                br_id = db.execute(
                    "INSERT INTO branches(book_id,parent_id,name,instruction,scope,"
                    "chapter_idx,para_idx,content,status,meta,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (bid, msg.get("parent_id"), msg.get("name", "我的改写"),
                     msg.get("instruction", ""), scope, msg.get("chapter_idx", 0),
                     msg.get("para_idx"), full, "ready",
                     db.jdumps(meta), now()))
                await ws_send(ws, "done", {"branch_id": br_id, "word_count": len(full)})
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001
        await ws_send(ws, "error", {"message": str(e)})


@router.websocket("/ws/chat/{bid}")
async def stream_chat(ws: WebSocket, bid: int):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            book = load_parsed_book(bid)
            st = get_structure(bid)
            q = msg.get("q", "")
            persona = msg.get("persona", "plot")
            scope = {"chapter_idx": msg["chapter_idx"]} if msg.get("chapter_idx") is not None else None
            result = qa.answer_question(q, st, book.chapters, persona, scope)
            await ws_send(ws, "meta", {"intent": result["intent"],
                                       "entities": result["entities"]})
            for ch in result["answer"]:
                await ws.send_text(json.dumps({"event": "delta", "delta": ch},
                                              ensure_ascii=False))
                await asyncio.sleep(0.012)
            await ws_send(ws, "refs", {"refs": result["refs"]})
            await ws_send(ws, "done", {})
    except WebSocketDisconnect:
        return
