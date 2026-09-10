"""书架与书籍管理 API。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import Response

from .. import db
from ..db import now
from ..schemas import BookPatch, ImportTextIn
from ..services import books as book_service
from ..services.covers import make_cover_svg
from ..parsers import parse_text

router = APIRouter(prefix="/api/books", tags=["books"])

ALLOWED_EXT = {".txt", ".md", ".markdown", ".epub", ".pdf"}


def _book_dict(row, analyze: dict | None = None) -> dict:
    d = dict(row)
    d["tags"] = db.jloads(d.get("tags"), [])
    d["meta"] = db.jloads(d.get("meta"), {})
    d["analyze"] = analyze or book_service.analyze_status(d["id"])
    # 阅读进度
    p = db.query_one("SELECT * FROM progress WHERE book_id=?", (d["id"],))
    d["progress"] = dict(p) if p else {"percent": 0, "chapter_idx": 0}
    return d


@router.get("")
def list_books(status: str | None = None, sort: str = "updated", q: str | None = None):
    sql, params = "SELECT * FROM books WHERE 1=1", []
    if status and status != "all":
        sql += " AND status=?"
        params.append(status)
    if q:
        sql += " AND (title LIKE ? OR author LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    order = {"updated": "updated_at DESC", "title": "title",
             "words": "word_count DESC", "created": "created_at DESC"}.get(sort, "updated_at DESC")
    sql += f" ORDER BY {order}"
    return [_book_dict(r) for r in db.query(sql, params)]


@router.post("/import")
async def import_books(files: list[UploadFile] = File(...)):
    created = []
    for f in files:
        suffix = Path(f.filename).suffix.lower()
        if suffix not in ALLOWED_EXT:
            raise HTTPException(400, f"暂不支持的格式：{f.filename}（支持 TXT/Markdown/EPUB/PDF）")
        data = await f.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        bid = book_service.import_file(tmp_path, original_name=f.filename)
        Path(tmp_path).unlink(missing_ok=True)
        created.append(bid)
    return {"created": created, "count": len(created)}


@router.post("/import/text")
def import_text(payload: ImportTextIn):
    parsed = parse_text(payload.text, "txt", payload.filename)
    if payload.title:
        parsed.title = payload.title
    if payload.author:
        parsed.author = payload.author
    bid = book_service.create_book(parsed, source_name=payload.filename)
    return {"created": [bid], "count": 1}


@router.get("/{bid}")
def get_book(bid: int):
    row = db.query_one("SELECT * FROM books WHERE id=?", (bid,))
    if not row:
        raise HTTPException(404, "书籍不存在")
    return _book_dict(row)


@router.patch("/{bid}")
def patch_book(bid: int, patch: BookPatch):
    row = db.query_one("SELECT * FROM books WHERE id=?", (bid,))
    if not row:
        raise HTTPException(404, "书籍不存在")
    fields, params = [], []
    for k in ("title", "author", "intro", "status"):
        v = getattr(patch, k)
        if v is not None:
            fields.append(f"{k}=?")
            params.append(v)
    if patch.tags is not None:
        fields.append("tags=?")
        params.append(db.jdumps(patch.tags))
    if patch.cover == "regenerate":
        fields.append("cover=?")
        params.append(make_cover_svg(patch.title or row["title"],
                                     patch.author or row["author"] or ""))
    if not fields:
        return {"ok": True}
    fields.append("updated_at=?")
    params += [now(), bid]
    db.execute(f"UPDATE books SET {', '.join(fields)} WHERE id=?", params)
    return {"ok": True}


@router.delete("/{bid}")
def delete_book(bid: int):
    for table in ("chapters", "analysis", "annotations", "chapter_summaries", "progress",
                  "bookmarks", "highlights", "branches", "sessions"):
        db.execute(f"DELETE FROM {table} WHERE book_id=?", (bid,))
    db.execute("DELETE FROM books WHERE id=?", (bid,))
    return {"ok": True}


@router.get("/{bid}/cover")
def book_cover(bid: int):
    row = db.query_one("SELECT cover,title FROM books WHERE id=?", (bid,))
    if not row:
        raise HTTPException(404)
    svg = row["cover"] or make_cover_svg(row["title"])
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/{bid}/analyze")
def analyze_status(bid: int):
    return book_service.analyze_status(bid)


@router.post("/{bid}/reanalyze")
def reanalyze(bid: int):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404)
    return book_service.reanalyze(bid)


@router.get("/{bid}/chapters")
def list_chapters(bid: int):
    rows = db.query(
        "SELECT idx,title,word_count,length(paragraphs) AS pl FROM chapters "
        "WHERE book_id=? ORDER BY idx", (bid,))
    return [{"idx": r["idx"], "title": r["title"], "word_count": r["word_count"]}
            for r in rows]


@router.get("/{bid}/chapters/{idx}")
def get_chapter(bid: int, idx: int):
    r = db.query_one(
        "SELECT idx,title,paragraphs,content FROM chapters WHERE book_id=? AND idx=?",
        (bid, idx))
    if not r:
        raise HTTPException(404, "章节不存在")
    return {"idx": r["idx"], "title": r["title"],
            "paragraphs": db.jloads(r["paragraphs"], []),
            "content": r["content"]}
