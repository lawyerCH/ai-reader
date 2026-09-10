"""读者分支 API：改写、分支树、版本切换与导出。"""
from __future__ import annotations

import io
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .. import db
from ..db import now
from ..schemas import BranchIn
from ..ai.loader import load_parsed_book, get_structure
from ..ai import rewrite as rw
from ..services.exporters import export_text, export_markdown, export_epub

router = APIRouter(prefix="/api/books/{bid}", tags=["branches"])


def _dh(filename: str) -> dict:
    return {"Content-Disposition":
            f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}"}


def _ctx(bid):
    if not db.query_one("SELECT id FROM books WHERE id=?", (bid,)):
        raise HTTPException(404, "书籍不存在")
    return load_parsed_book(bid), get_structure(bid)


@router.post("/branches")
def create_branch(bid: int, payload: BranchIn):
    book, st = _ctx(bid)
    original = payload.original_text
    if payload.scope == "paragraph" and not original and payload.para_idx is not None:
        ch = db.query_one(
            "SELECT paragraphs FROM chapters WHERE book_id=? AND idx=?",
            (bid, payload.chapter_idx))
        paras = db.jloads(ch["paragraphs"], []) if ch else []
        if 0 <= payload.para_idx < len(paras):
            original = paras[payload.para_idx]
    result = rw.rewrite(payload.scope, payload.instruction, st,
                       original_text=original, chapter_idx=payload.chapter_idx)
    br_id = db.execute(
        "INSERT INTO branches(book_id,parent_id,name,instruction,scope,chapter_idx,"
        "para_idx,end_chapter_idx,content,status,meta,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (bid, payload.parent_id, payload.name or "我的改写", payload.instruction,
         payload.scope, payload.chapter_idx, payload.para_idx, payload.end_chapter_idx,
         result["text"], "ready", db.jdumps({"plan": result["plan"],
                                            "word_count": result["word_count"]}),
         now()))
    return {"id": br_id, **result}


@router.get("/branches")
def list_branches(bid: int):
    _ctx(bid)
    rows = [dict(r) for r in db.query(
        "SELECT * FROM branches WHERE book_id=? ORDER BY id", (bid,))]
    for r in rows:
        r["meta"] = db.jloads(r.get("meta"), {})
    return rows


@router.get("/branches/tree")
def branch_tree(bid: int):
    _ctx(bid)
    rows = db.query("SELECT id,parent_id,name,scope,chapter_idx,instruction,created_at "
                    "FROM branches WHERE book_id=? ORDER BY id", (bid,))
    nodes = [dict(r) for r in rows]
    # 原版虚拟根
    root = {"id": 0, "parent_id": None, "name": "原版", "scope": "original",
            "chapter_idx": 0, "instruction": "", "children": []}
    idx = {0: root}
    for n in nodes:
        n["children"] = []
        idx[n["id"]] = n
    for n in nodes:
        parent = n.get("parent_id") or 0
        idx.setdefault(parent, root)["children"].append(n)
    return root


@router.get("/branches/{br_id}")
def get_branch(bid: int, br_id: int):
    r = db.query_one("SELECT * FROM branches WHERE id=? AND book_id=?", (br_id, bid))
    if not r:
        raise HTTPException(404)
    d = dict(r)
    d["meta"] = db.jloads(d.get("meta"), {})
    return d


@router.delete("/branches/{br_id}")
def delete_branch(bid: int, br_id: int):
    # 子分支挂回父节点
    r = db.query_one("SELECT parent_id FROM branches WHERE id=? AND book_id=?",
                     (br_id, bid))
    if not r:
        raise HTTPException(404)
    db.execute("UPDATE branches SET parent_id=? WHERE parent_id=?", (r["parent_id"], br_id))
    db.execute("DELETE FROM branches WHERE id=?", (br_id,))
    return {"ok": True}


@router.get("/branches/{br_id}/materialized")
def materialized(bid: int, br_id: int):
    """沿分支树根路径汇总所有改写覆盖，前端按 (chapter,para) 覆盖原版。"""
    book, _ = _ctx(bid)
    chain = []
    cur = br_id
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        r = db.query_one("SELECT * FROM branches WHERE id=? AND book_id=?", (cur, bid))
        if not r:
            break
        chain.append(dict(r))
        cur = r["parent_id"]
    chain.reverse()
    overrides = []
    for r in chain:
        paras = [p for p in r["content"].split("\n") if p.strip()]
        overrides.append({
            "branch_id": r["id"], "name": r["name"], "scope": r["scope"],
            "chapter_idx": r["chapter_idx"], "para_idx": r["para_idx"],
            "instruction": r["instruction"],
            "paragraphs": paras,
            "start_para": r["para_idx"],
        })
    return {"branch_id": br_id, "overrides": overrides}


@router.get("/branches/{br_id}/export")
def export_branch(bid: int, br_id: int, format: str = "markdown"):
    book, _ = _ctx(bid)
    r = db.query_one("SELECT * FROM branches WHERE id=? AND book_id=?", (br_id, bid))
    if not r:
        raise HTTPException(404)
    filename = f"{book.title}-{r['name']}"
    if format == "txt":
        data = export_text(book, r, mode="branch")
        return Response(content=data, media_type="text/plain; charset=utf-8",
                        headers=_dh(f"{filename}.txt"))
    if format == "epub":
        data = export_epub(book, r, mode="branch")
        return Response(content=data, media_type="application/epub+zip",
                        headers=_dh(f"{filename}.epub"))
    data = export_markdown(book, r, mode="branch")
    return Response(content=data, media_type="text/markdown; charset=utf-8",
                    headers=_dh(f"{filename}.md"))
