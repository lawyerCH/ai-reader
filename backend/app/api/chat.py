"""AI 问答与讨论 API：单角色问答、多角色读书会、角色辩论、脑洞、预测。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..db import now
from ..schemas import AskIn, DiscussIn, DebateIn, WhatIfIn
from ..ai.loader import load_parsed_book, get_structure
from ..ai import qa

router = APIRouter(prefix="/api/books/{bid}", tags=["chat"])


def _ctx(bid: int):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404, "书籍不存在")
    book = load_parsed_book(bid)
    st = get_structure(bid)
    return book, st


@router.post("/ask")
def ask(bid: int, payload: AskIn):
    book, st = _ctx(bid)
    scope = {"chapter_idx": payload.chapter_idx} if payload.chapter_idx is not None else None
    result = qa.answer_question(payload.q, st, book.chapters, payload.persona, scope)
    cid = payload.conversation_id
    if cid:
        _persist(cid, payload.q, payload.persona, result)
    return result


@router.post("/discuss")
def discuss(bid: int, payload: DiscussIn):
    """读书会：同一问题，多个角色各自表态。"""
    book, st = _ctx(bid)
    scope = {"chapter_idx": payload.chapter_idx} if payload.chapter_idx is not None else None
    answers = qa.multi_persona(payload.q, st, book.chapters, payload.personas, scope)
    return {"q": payload.q, "answers": answers}


@router.post("/debate")
def debate(bid: int, payload: DebateIn):
    book, st = _ctx(bid)
    return qa.debate(payload.topic, st, book.chapters,
                     payload.side_a, payload.side_b,
                     {"chapter_idx": payload.chapter_idx} if payload.chapter_idx is not None else None)


@router.post("/whatif")
def what_if(bid: int, payload: WhatIfIn):
    book, st = _ctx(bid)
    return {"hypothesis": payload.hypothesis,
            "answers": qa.what_if(payload.hypothesis, st, book.chapters)}


@router.get("/predict")
def predict(bid: int):
    book, st = _ctx(bid)
    return {"predictions": qa.answer_question("预测后续剧情", st, book.chapters, "plot")}


# ---------- 会话持久化 ----------

@router.post("/conversations")
def create_conversation(bid: int, scope: str = "book", anchor: str = "", title: str = ""):
    cid = db.execute(
        "INSERT INTO conversations(book_id,scope,anchor,title,created_at) VALUES(?,?,?,?,?)",
        (bid, scope, anchor, title or "新的读书会", now()))
    return {"id": cid}


@router.get("/conversations")
def list_conversations(bid: int):
    return [dict(r) for r in db.query(
        "SELECT * FROM conversations WHERE book_id=? ORDER BY id DESC", (bid,))]


@router.get("/conversations/{cid}")
def get_conversation(bid: int, cid: int):
    msgs = [dict(r) for r in db.query(
        "SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (cid,))]
    for m in msgs:
        m["refs"] = db.jloads(m["refs"], [])
    return {"messages": msgs}


def _persist(cid: int, question: str, persona: str, result: dict):
    db.execute(
        "INSERT INTO messages(conversation_id,role,persona,content,refs,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (cid, "user", "", question, "[]", now()))
    db.execute(
        "INSERT INTO messages(conversation_id,role,persona,content,refs,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (cid, "persona", persona, result["answer"], db.jdumps(result.get("refs", [])), now()))
