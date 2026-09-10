"""阅读进度、书签、划线高亮、阅读统计 API。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from .. import db
from ..db import now
from ..schemas import ProgressIn, BookmarkIn, HighlightIn, SessionIn

router = APIRouter(prefix="/api", tags=["reader"])


def _book(bid: int):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404, "书籍不存在")


@router.put("/books/{bid}/progress")
def put_progress(bid: int, p: ProgressIn):
    _book(bid)
    db.execute(
        "INSERT OR REPLACE INTO progress(book_id,chapter_idx,para_idx,offset,percent,updated_at)"
        " VALUES(?,?,?,?,?,?)",
        (bid, p.chapter_idx, p.para_idx, p.offset, p.percent, now()))
    db.execute("UPDATE books SET last_read_at=?, status=CASE WHEN status='want' THEN 'reading' "
               "ELSE status END WHERE id=?", (now(), bid))
    return {"ok": True}


@router.get("/books/{bid}/progress")
def get_progress(bid: int):
    r = db.query_one("SELECT * FROM progress WHERE book_id=?", (bid,))
    return dict(r) if r else {"percent": 0, "chapter_idx": 0, "para_idx": 0}


@router.get("/books/{bid}/bookmarks")
def list_bookmarks(bid: int):
    return [dict(r) for r in db.query(
        "SELECT * FROM bookmarks WHERE book_id=? ORDER BY chapter_idx,para_idx", (bid,))]


@router.post("/books/{bid}/bookmarks")
def add_bookmark(bid: int, p: BookmarkIn):
    _book(bid)
    i = db.execute(
        "INSERT INTO bookmarks(book_id,chapter_idx,para_idx,preview,note,created_at)"
        " VALUES(?,?,?,?,?,?)",
        (bid, p.chapter_idx, p.para_idx, p.preview, p.note, now()))
    return {"id": i}


@router.delete("/books/{bid}/bookmarks/{mid}")
def del_bookmark(bid: int, mid: int):
    db.execute("DELETE FROM bookmarks WHERE id=? AND book_id=?", (mid, bid))
    return {"ok": True}


@router.get("/books/{bid}/highlights")
def list_highlights(bid: int):
    return [dict(r) for r in db.query(
        "SELECT * FROM highlights WHERE book_id=? ORDER BY chapter_idx,para_idx", (bid,))]


@router.post("/books/{bid}/highlights")
def add_highlight(bid: int, p: HighlightIn):
    _book(bid)
    i = db.execute(
        "INSERT INTO highlights(book_id,chapter_idx,para_idx,start,length,text,color,note,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (bid, p.chapter_idx, p.para_idx, p.start, p.length, p.text, p.color, p.note, now()))
    return {"id": i}


@router.delete("/books/{bid}/highlights/{hid}")
def del_highlight(bid: int, hid: int):
    db.execute("DELETE FROM highlights WHERE id=? AND book_id=?", (hid, bid))
    return {"ok": True}


@router.post("/books/{bid}/sessions")
def report_session(bid: int, s: SessionIn):
    _book(bid)
    day = date.today().isoformat()
    r = db.query_one("SELECT id,seconds,words FROM sessions WHERE book_id=? AND day=?",
                     (bid, day))
    if r:
        db.execute("UPDATE sessions SET seconds=?,words=? WHERE id=?",
                   (r["seconds"] + s.seconds, r["words"] + s.words, r["id"]))
    else:
        db.execute("INSERT INTO sessions(book_id,day,seconds,words) VALUES(?,?,?,?)",
                   (bid, day, s.seconds, s.words))
    return {"ok": True}


# ---------------- 全局看板 ----------------

@router.get("/stats/overview")
def stats_overview():
    books = db.query("SELECT * FROM books")
    n_finished = sum(1 for b in books if b["status"] == "finished")
    words_read = db.query_one("SELECT COALESCE(SUM(words),0) w FROM sessions")["w"]
    seconds = db.query_one("SELECT COALESCE(SUM(seconds),0) s FROM sessions")["s"]
    days = db.query_one("SELECT COUNT(DISTINCT day) d FROM sessions")["d"]
    # 按日聚合
    daily = [dict(r) for r in db.query(
        "SELECT day, SUM(seconds) seconds, SUM(words) words FROM sessions GROUP BY day ORDER BY day")]
    # 批注互动
    persona_rows = db.query(
        "SELECT persona, COUNT(*) n FROM annotations GROUP BY persona")
    persona_stats = {r["persona"]: r["n"] for r in persona_rows}
    n_branches = db.query_one("SELECT COUNT(*) n FROM branches")["n"]
    branch_words = db.query_one(
        "SELECT COALESCE(SUM(length(content)),0) w FROM branches")["w"]
    # 题材/偏好（按书名与高频人物词简单统计）
    tags = {}
    for b in books:
        for t in db.jloads(b["tags"], []):
            tags[t] = tags.get(t, 0) + 1
    return {
        "book_count": len(books),
        "finished_count": n_finished,
        "reading_count": sum(1 for b in books if b["status"] == "reading"),
        "total_words": sum(b["word_count"] for b in books),
        "words_read": words_read,
        "total_seconds": seconds,
        "active_days": days,
        "daily": daily,
        "annotation_by_persona": persona_stats,
        "branch_count": n_branches,
        "branch_words": branch_words,
        "tags": tags,
    }


@router.get("/stats/books/{bid}")
def stats_book(bid: int):
    rows = [dict(r) for r in db.query(
        "SELECT day,seconds,words FROM sessions WHERE book_id=? ORDER BY day", (bid,))]
    n_ann = db.query_one("SELECT COUNT(*) n FROM annotations WHERE book_id=?", (bid,))["n"]
    n_br = db.query_one("SELECT COUNT(*) n FROM branches WHERE book_id=?", (bid,))["n"]
    hl = db.query_one("SELECT COUNT(*) n, COALESCE(SUM(length),0) l FROM highlights WHERE book_id=?",
                      (bid,))
    return {"daily": rows, "annotation_count": n_ann, "branch_count": n_br,
            "highlight_count": hl["n"], "highlight_chars": hl["l"]}
